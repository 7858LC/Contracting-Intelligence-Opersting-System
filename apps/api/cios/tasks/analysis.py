"""Full opportunity analysis task — orchestrates CEO Agent pipeline."""

import asyncio
import uuid

from cios.tasks import celery_app

_VALID_RECOMMENDATIONS = {"BID", "NO_BID", "CONDITIONAL_BID"}


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30, soft_time_limit=600)
def run_opportunity_analysis(self, tenant_id: str, user_id: str, opportunity_id: str) -> dict:
    try:
        return asyncio.run(_run_async(tenant_id, user_id, opportunity_id))
    except Exception as exc:
        # max_retries was declared but nothing ever called self.retry() — see
        # bid_analysis.py's identical fix. A transient failure (or a JSON
        # parse failure below) used to just complete silently with every
        # score left blank instead of actually retrying.
        raise self.retry(exc=exc)


async def _run_async(tenant_id: str, user_id: str, opportunity_id: str) -> dict:
    from datetime import UTC, datetime

    from sqlalchemy import select, text

    from cios.agents.base import AgentContext
    from cios.agents.ceo_agent import CEOAgent
    from cios.core.database import async_session_factory
    from cios.models.opportunity import Opportunity
    from cios.vector.tenant_store import TenantVectorStore

    async with async_session_factory() as db:
        # opportunities has FORCE ROW LEVEL SECURITY (migration 007).
        # app.current_tenant is normally set by get_current_user's SET LOCAL
        # on the request's session — this task runs outside that request
        # lifecycle on its own session, so without this the query below
        # silently returns zero rows (RLS, not a real "not found") and the
        # task exits early having written nothing. See bid_analysis.py.
        await db.execute(
            text("SELECT set_config('app.current_tenant', :tenant_id, false)"),
            {"tenant_id": tenant_id},
        )

        result = await db.execute(
            select(Opportunity).where(Opportunity.id == uuid.UUID(opportunity_id))
        )
        opp = result.scalar_one_or_none()
        if not opp:
            return {"error": "opportunity not found"}

        opportunity_data = opp.to_dict()

        store = TenantVectorStore(tenant_id)
        try:
            knowledge_context = await store.search(
                query=f"{opportunity_data.get('title', '')} {opportunity_data.get('agency', '')}",
                top_k=15,
            )
        except Exception:
            knowledge_context = []

        context = AgentContext(
            tenant_id=uuid.UUID(tenant_id),
            user_id=uuid.UUID(user_id),
            opportunity_id=uuid.UUID(opportunity_id),
            rule_pack=opportunity_data.get("procurement_rule_pack", "us_federal_far"),
        )

        ceo = CEOAgent()
        output = await ceo.orchestrate_full_assessment(context, opportunity_data, knowledge_context)

        synthesis = output.get("synthesis", {})
        result_data = synthesis.get("result", {})

        from cios.agents.json_parsing import extract_claude_json

        # require_any_of: a response that parses as JSON but matches none of
        # the schema keys must FAIL (and retry via self.retry() in the task
        # wrapper above) rather than sail through — every .get() below would
        # return None, and the row would commit as "analyzed" with every
        # score and the recommendation silently null. See bid_analysis.py,
        # which shipped that exact all-null-but-analyzed row once already.
        parsed = extract_claude_json(
            result_data.get("executive_summary", "") or "",
            context="Opportunity analysis (CEO synthesis)",
            require_any_of=frozenset(
                {
                    "gate_review_recommendation",
                    "award_probability",
                    "confidence_score",
                    "strategic_recommendation",
                }
            ),
        )

        # Same shape guard as bid_analysis.py's recommendation handling —
        # only ever accept one of the three known values; anything else
        # becomes None rather than corrupting a column the frontend treats
        # as a closed enum for color/label lookups.
        recommendation = parsed.get("gate_review_recommendation")
        if isinstance(recommendation, str):
            normalized = recommendation.strip().upper().replace(" ", "_").replace("-", "_")
            recommendation = normalized if normalized in _VALID_RECOMMENDATIONS else None
        else:
            recommendation = None

        opp.award_probability_score = parsed.get("award_probability")
        opp.bid_no_bid_recommendation = recommendation
        opp.evidence = {"ceo_synthesis": str(result_data)[:3000]}
        opp.confidence_score = parsed.get("confidence_score")
        opp.ai_model_version = CEOAgent.model
        opp.analyzed_at = datetime.now(UTC)

        await db.commit()
        return {"opportunity_id": opportunity_id, "status": "completed"}
