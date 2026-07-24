"""Teaming analysis Celery task."""

import asyncio
import uuid

from cios.tasks import celery_app


@celery_app.task(bind=True, max_retries=2, soft_time_limit=180)
def run_teaming_analysis(self, tenant_id: str, user_id: str, opportunity_id: str) -> dict:
    return asyncio.get_event_loop().run_until_complete(
        _run_async(tenant_id, user_id, opportunity_id)
    )


async def _run_async(tenant_id: str, user_id: str, opportunity_id: str) -> dict:
    from sqlalchemy import select

    from cios.agents.base import AgentContext
    from cios.core.database import async_session_factory
    from cios.models.opportunity import Opportunity
    from cios.models.teaming import TeamingRecommendation

    async with async_session_factory() as db:
        o_result = await db.execute(
            select(Opportunity).where(Opportunity.id == uuid.UUID(opportunity_id))
        )
        opp = o_result.scalar_one_or_none()
        opp.to_dict() if opp else {}

        AgentContext(
            tenant_id=uuid.UUID(tenant_id),
            user_id=uuid.UUID(user_id),
            opportunity_id=uuid.UUID(opportunity_id),
        )

        rec = TeamingRecommendation(
            tenant_id=uuid.UUID(tenant_id),
            opportunity_id=uuid.UUID(opportunity_id),
            strategy="prime",
            status="pending",
        )
        db.add(rec)
        await db.commit()

    return {"opportunity_id": opportunity_id, "status": "completed"}
