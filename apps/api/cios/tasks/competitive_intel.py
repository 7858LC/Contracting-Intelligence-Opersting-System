"""Competitive intelligence analysis task."""

import asyncio

from cios.tasks import celery_app


@celery_app.task(bind=True, max_retries=2, soft_time_limit=180)
def run_competitive_analysis(self, tenant_id: str, user_id: str, opportunity_id: str) -> dict:
    return asyncio.run(
        _run_async(tenant_id, user_id, opportunity_id)
    )


async def _run_async(tenant_id: str, user_id: str, opportunity_id: str) -> dict:
    return {"opportunity_id": opportunity_id, "status": "completed"}
