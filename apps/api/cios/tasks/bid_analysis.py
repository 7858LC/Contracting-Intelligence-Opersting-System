"""Bid/No-Bid analysis Celery task."""

import asyncio
import uuid

from cios.tasks import celery_app

_VALID_RECOMMENDATIONS = {"BID", "NO_BID", "CONDITIONAL_BID"}


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30, soft_time_limit=600)
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

    from sqlalchemy import select, text

    from cios.agents.base import AgentContext
    from cios.agents.directors.capture_director import CaptureDirector
    from cios.agents.directors.risk_director import RiskDirector
    from cios.core.database import async_session_factory
    from cios.models.bid_decision import BidDecision
    from cios.models.opportunity import Opportunity

    async with async_session_factory() as db:
        # bid_decisions and opportunities both FORCE ROW LEVEL SECURITY
        # (migration 007). app.current_tenant is normally set by
        # get_current_user's SET LOCAL on the request's session — this task
        # runs outside that request lifecycle on its own session, so without
        # this the queries below silently return zero rows (RLS, not a real
        # "not found") and the task exits early having written nothing.
        await db.execute(
            text("SELECT set_config('app.current_tenant', :tenant_id, false)"),
            {"tenant_id": tenant_id},
        )

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

        # require_any_of: a response that parses as JSON but matches none of
        # the schema keys must FAIL (and retry) here, not sail through — every
        # .get() below would return None, and the row would commit as
        # "analyzed" with every score, the recommendation, and the rationale
        # all silently null. That exact all-null-but-analyzed row shape
        # shipped live from this task once already (when parse failures were
        # swallowed into {}); this guard closes the last remaining path to it.
        c = extract_claude_json(
            capture_out.get("result", {}).get("capture_assessment", "") or "",
            context="Bid analysis (capture)",
            require_any_of=frozenset(
                {
                    "strategic_fit_score",
                    "win_probability_score",
                    "past_performance_score",
                    "capability_match_score",
                    "bid_no_bid_recommendation",
                    "recommendation_rationale",
                    "confidence_score",
                }
            ),
        )
        r = extract_claude_json(
            risk_out.get("result", {}).get("risk_assessment", "") or "",
            context="Bid analysis (risk)",
            require_any_of=frozenset({"risk_score", "risks"}),
        )

        decision.strategic_fit_score = c.get("strategic_fit_score")
        decision.win_probability_score = c.get("win_probability_score")
        decision.past_performance_score = c.get("past_performance_score")
        decision.capability_match_score = c.get("capability_match_score")
        decision.risk_score = r.get("risk_score")

        # Prompt now pins this to a plain "BID"/"NO_BID"/"CONDITIONAL_BID"
        # string (see capture_director.py), but a nested object — or any
        # other off-schema value — slipping through anyway must not crash the
        # write and lose every other score in the same commit, which it did
        # live (DataError: "expected str, got dict") because this used to
        # assign the raw value straight into a String column with no shape
        # check at all. Only ever accept one of the three known values;
        # anything else (a stray free-text phrase pulled out of a nested
        # object, for instance) becomes None rather than corrupting a column
        # the frontend treats as a closed enum for icon/color lookups.
        recommendation = c.get("bid_no_bid_recommendation")
        if isinstance(recommendation, dict):
            recommendation = (
                recommendation.get("recommendation")
                or recommendation.get("decision")
                or recommendation.get("value")
            )
        if isinstance(recommendation, str):
            normalized = recommendation.strip().upper().replace(" ", "_").replace("-", "_")
            recommendation = normalized if normalized in _VALID_RECOMMENDATIONS else None
        else:
            recommendation = None
        decision.recommendation = recommendation
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
