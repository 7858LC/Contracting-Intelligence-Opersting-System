"""Initial onboarding analysis task."""

import asyncio

from cios.tasks import celery_app


@celery_app.task(bind=True, soft_time_limit=300)
def run_initial_analysis(self, tenant_id: str) -> dict:
    return asyncio.get_event_loop().run_until_complete(_run_async(tenant_id))


async def _run_async(tenant_id: str) -> dict:
    return {"tenant_id": tenant_id, "status": "initial_analysis_complete"}
