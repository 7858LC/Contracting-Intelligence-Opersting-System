"""Bid/No-Bid analysis Celery task."""

import asyncio
import uuid

from cios.tasks import celery_app


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30, soft_time_limit=300)
def run_bid_analysis(self, tenant_id: str, user_id: str, decision_id: str) -> dict:
    try:
        return asyncio.run(_run_async(tenant_id, user_id, decision_id))
    except Exception as exc:
        # Previously unwired — max_retries was declared but nothing ever
        # called self.retry(), so a transient failure (or, before the JSON
        # parsing fix below, every single run) just completed silently with
        # every score left blank instead of actually retrying.
        raise self.retry(exc=exc)


async def _run_async(tenant_id: str, user_id: str, decision_id: str) -> dict:
    from datetime import UTC, datetime

    from sqlalchemy import select

    from cios.agents.base import AgentContext
    from cios.agents.directors.capture_director import CaptureDirector
    from cios.agents.directors.risk_director import RiskDirector
    from cios.core.database import async_session_factory
    from cios.models.bid_decision import BidDecision
    from cios.models.opportunity import Opportunity

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

        capture_out = await capture.run(
            context, opportunity_data=opportunity_data, knowledge_context=[]
        )
        risk_out = await risk.run(context, opportunity_data=opportunity_data, knowledge_context=[])

        from cios.agents.json_parsing import extract_claude_json

        c = extract_claude_json(
            capture_out.get("result", {}).get("capture_assessment", "") or "",
            context="Bid analysis (capture)",
        )
        r = extract_claude_json(
            risk_out.get("result", {}).get("risk_assessment", "") or "",
            context="Bid analysis (risk)",
        )

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

        # Weighted composite over whatever factors actually got scored — only
        # 5 of the 8 factor slots (competitive_position/cost_of_bid/relationship
        # aren't produced by any agent yet) have a value at this point, so
        # normalize over the scored factors' weight instead of assuming all 8,
        # which would silently understate the score.
        weights = decision.scoring_weights or {}
        scored_factors = {
            "strategic_fit": decision.strategic_fit_score,
            "win_probability": decision.win_probability_score,
            "past_performance": decision.past_performance_score,
            "capability_match": decision.capability_match_score,
            "competitive_position": decision.competitive_position_score,
            "cost_of_bid": decision.cost_of_bid_score,
            "risk": decision.risk_score,
            "relationship": decision.relationship_score,
        }
        weighted_sum = 0.0
        weight_total = 0.0
        for key, score in scored_factors.items():
            if score is None:
                continue
            w = weights.get(key, 0.0)
            weighted_sum += score * w
            weight_total += w
        decision.composite_score = (
            round(weighted_sum / weight_total, 1) if weight_total > 0 else None
        )
        decision.analyzed_at = datetime.now(UTC)

        await db.commit()
        return {"decision_id": decision_id, "status": "completed"}
