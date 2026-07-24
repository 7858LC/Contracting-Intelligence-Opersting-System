"""Full opportunity analysis task — orchestrates CEO Agent pipeline."""

import asyncio
import uuid

from cios.tasks import celery_app


@celery_app.task(bind=True, max_retries=2, soft_time_limit=600)
def run_opportunity_analysis(self, tenant_id: str, user_id: str, opportunity_id: str) -> dict:
    return asyncio.get_event_loop().run_until_complete(
        _run_async(tenant_id, user_id, opportunity_id)
    )


async def _run_async(tenant_id: str, user_id: str, opportunity_id: str) -> dict:
    from sqlalchemy import select

    from cios.agents.base import AgentContext
    from cios.agents.ceo_agent import CEOAgent
    from cios.core.database import async_session_factory
    from cios.models.opportunity import Opportunity
    from cios.vector.tenant_store import TenantVectorStore

    async with async_session_factory() as db:
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

        import json

        try:
            exec_summary = result_data.get("executive_summary", "")
            parsed = json.loads(exec_summary) if isinstance(exec_summary, str) else exec_summary
        except Exception:
            parsed = {}

        opp.award_probability_score = parsed.get("award_probability")
        opp.bid_no_bid_recommendation = parsed.get("gate_review_recommendation")
        opp.evidence = {"ceo_synthesis": str(result_data)[:3000]}
        opp.confidence_score = parsed.get("confidence_score")
        opp.ai_model_version = CEOAgent.model

        await db.commit()
        return {"opportunity_id": opportunity_id, "status": "completed"}
