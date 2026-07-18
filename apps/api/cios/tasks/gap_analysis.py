"""Capability gap analysis task."""
import asyncio, uuid
from cios.tasks import celery_app


@celery_app.task(bind=True, max_retries=2, soft_time_limit=180)
def run_capability_gap_analysis(self, tenant_id: str, user_id: str, opportunity_id: str) -> dict:
    return asyncio.get_event_loop().run_until_complete(
        _run_async(tenant_id, user_id, opportunity_id)
    )


async def _run_async(tenant_id: str, user_id: str, opportunity_id: str) -> dict:
    return {"opportunity_id": opportunity_id, "status": "completed"}
