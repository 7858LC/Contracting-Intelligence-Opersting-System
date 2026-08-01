"""Onboarding-complete task.

Previously returned a hardcoded {"status": "initial_analysis_complete"}
without touching the database or sending anything — completing onboarding
did nothing observable. There's no meaningful AI analysis to run yet at
account-creation time (no opportunity assigned, no evidence documents
uploaded for Winning Profile Hypothesis to work from), so the real
replacement is a confirmation email summarizing what the tenant actually
entered during onboarding — see api/v1/endpoints/onboarding.py for where
that data gets persisted (Capability/PastPerformance/Competitor/
TeamingPartner rows) before this task ever runs.
"""

import asyncio
import uuid

from cios.tasks import celery_app


@celery_app.task(bind=True, soft_time_limit=60)
def run_initial_analysis(self, tenant_id: str) -> dict:
    return asyncio.run(_run_async(tenant_id))


async def _run_async(tenant_id: str) -> dict:
    from sqlalchemy import func, select, text

    from cios.core.database import async_session_factory
    from cios.models.capability import Capability
    from cios.models.competitor import Competitor
    from cios.models.past_performance import PastPerformance
    from cios.models.teaming import TeamingPartner
    from cios.models.tenant import TenantMember

    tid = uuid.UUID(tenant_id)
    async with async_session_factory() as db:
        # capabilities/past_performances/competitors/teaming_partners all
        # FORCE ROW LEVEL SECURITY — this task runs outside the request
        # lifecycle on its own session.
        await db.execute(
            text("SELECT set_config('app.current_tenant', :tenant_id, false)"),
            {"tenant_id": tenant_id},
        )

        summary = {
            "capabilities": (
                await db.execute(
                    select(func.count(Capability.id)).where(Capability.tenant_id == tid)
                )
            ).scalar_one(),
            "past_performance": (
                await db.execute(
                    select(func.count(PastPerformance.id)).where(PastPerformance.tenant_id == tid)
                )
            ).scalar_one(),
            "competitors": (
                await db.execute(
                    select(func.count(Competitor.id)).where(Competitor.tenant_id == tid)
                )
            ).scalar_one(),
            "teaming_partners": (
                await db.execute(
                    select(func.count(TeamingPartner.id)).where(TeamingPartner.tenant_id == tid)
                )
            ).scalar_one(),
        }

        owner = (
            (
                await db.execute(
                    select(TenantMember).where(
                        TenantMember.tenant_id == tid, TenantMember.role == "owner"
                    )
                )
            )
            .scalars()
            .first()
        )

    if owner:
        from cios.tasks.email import send_onboarding_welcome_email

        send_onboarding_welcome_email.delay(tenant_id, owner.email, summary)

    return {"tenant_id": tenant_id, "status": "initial_analysis_complete", "summary": summary}
