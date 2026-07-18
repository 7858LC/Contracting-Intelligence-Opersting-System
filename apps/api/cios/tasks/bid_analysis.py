"""Bid/No-Bid analysis Celery task."""
import asyncio, uuid
from cios.tasks import celery_app


@celery_app.task(bind=True, max_retries=2, soft_time_limit=300)
def run_bid_analysis(self, tenant_id: str, user_id: str, decision_id: str) -> dict:
    return asyncio.get_event_loop().run_until_complete(
        _run_async(tenant_id, user_id, decision_id)
    )


async def _run_async(tenant_id: str, user_id: str, decision_id: str) -> dict:
    from cios.core.database import async_session_factory
    from cios.agents.directors.capture_director import CaptureDirector
    from cios.agents.directors.risk_director import RiskDirector
    from cios.agents.base import AgentContext
    from cios.models.bid_decision import BidDecision
    from cios.models.opportunity import Opportunity
    from sqlalchemy import select

    async with async_session_factory() as db:
        d_result = await db.execute(
            select(BidDecision).where(BidDecision.id == uuid.UUID(decision_id))
        )
        decision = d_result.scalar_one_or_none()
        if not decision:
            return {"error": "decision not found"}

        o_result = await db.execute(
            select(Opportunity).where(Opportunity.id == decision.opportunity_id)
        )
        opp = o_result.scalar_one_or_none()
        opportunity_data = opp.to_dict() if opp else {}

        context = AgentContext(
            tenant_id=uuid.UUID(tenant_id),
            user_id=uuid.UUID(user_id),
            opportunity_id=decision.opportunity_id,
        )

        capture = CaptureDirector()
        risk = RiskDirector()

        capture_out = await capture.run(context, opportunity_data=opportunity_data, knowledge_context=[])
        risk_out = await risk.run(context, opportunity_data=opportunity_data, knowledge_context=[])

        import json
        try:
            c = json.loads(capture_out.get("result", {}).get("capture_assessment", "{}") or "{}")
            r = json.loads(risk_out.get("result", {}).get("risk_assessment", "{}") or "{}")
        except Exception:
            c, r = {}, {}

        decision.strategic_fit_score = c.get("strategic_fit_score")
        decision.win_probability_score = c.get("win_probability_score")
        decision.past_performance_score = c.get("past_performance_score")
        decision.capability_match_score = c.get("capability_match_score")
        decision.risk_score = r.get("risk_score")
        decision.recommendation = c.get("bid_no_bid_recommendation")
        decision.recommendation_rationale = c.get("recommendation_rationale")
        decision.risks = r.get("risks", [])
        decision.evidence = {"capture": str(c)[:1000], "risk": str(r)[:1000]}
        decision.confidence_score = c.get("confidence_score")
        decision.ai_model_version = CaptureDirector.model

        await db.commit()
        return {"decision_id": decision_id, "status": "completed"}
