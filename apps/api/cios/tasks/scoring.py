"""Scoring tasks."""

import asyncio

from cios.tasks import celery_app


@celery_app.task(bind=True, max_retries=2)
def score_pp_relevance(self, tenant_id: str, pp_id: str, opportunity_id: str) -> dict:
    return asyncio.get_event_loop().run_until_complete(_run_async(tenant_id, pp_id, opportunity_id))


async def _run_async(tenant_id: str, pp_id: str, opportunity_id: str) -> dict:
    return {"pp_id": pp_id, "opportunity_id": opportunity_id, "status": "completed"}
