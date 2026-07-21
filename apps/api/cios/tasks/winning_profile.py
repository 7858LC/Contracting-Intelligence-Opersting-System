"""Winning Profile Hypothesis™ Celery tasks.

The evidence-fusion pipeline is fast and deterministic, so the API runs it
synchronously. This task exists for bulk/async execution (e.g. re-running the
hypothesis for many solicitations after new evidence lands) and for optional
Claude narrative enrichment off the request path.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import structlog

from cios.tasks import celery_app

log = structlog.get_logger(__name__)


def _run(coro: Any) -> Any:
    return asyncio.get_event_loop().run_until_complete(coro)


@celery_app.task(
    name="cios.tasks.winning_profile.run_pipeline",
    queue="analysis",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def run_pipeline(
    self,
    solicitation_id: str,
    tenant_id: str,
    target_contractor_id: str | None = None,
    enrich: bool = False,
) -> dict:
    """Run the full pre-award pipeline for one solicitation and persist results."""
    try:
        return _run(
            _async_run_pipeline(
                uuid.UUID(solicitation_id),
                uuid.UUID(tenant_id),
                uuid.UUID(target_contractor_id) if target_contractor_id else None,
                enrich,
            )
        )
    except Exception as exc:  # noqa: BLE001
        log.error("wph_pipeline_failed", solicitation_id=solicitation_id, error=str(exc))
        raise self.retry(exc=exc)


async def _async_run_pipeline(
    solicitation_id: uuid.UUID,
    tenant_id: uuid.UUID,
    target_contractor_id: uuid.UUID | None,
    enrich: bool,
) -> dict:
    from cios.core.database import async_session_factory
    from cios.models.winning_profile import WPHSolicitation
    from cios.wph.constants import PipelineStatus
    from cios.wph.service import WPHService

    async with async_session_factory() as db:
        sol = await db.get(WPHSolicitation, solicitation_id)
        if not sol or sol.tenant_id != tenant_id:
            return {"error": "Solicitation not found"}

        service = WPHService(db)
        try:
            await service.extract_signals(sol, tenant_id)
            profile = await service.generate_profile(sol, tenant_id)

            if enrich:
                from cios.agents.winning_profile_agent import enrich_profile_narrative

                pdc = await service.load_profile_dataclass(profile, tenant_id)
                narrative = await enrich_profile_narrative(
                    pdc, tenant_id, {"title": sol.title, "agency": sol.agency}
                )
                if narrative:
                    profile.narrative = narrative
                    profile.model_used = "claude-sonnet-4-6"
                    await db.commit()

            alignments = await service.align_contractors(sol, profile, tenant_id)
            assessment = None
            if alignments:
                assessment = await service.assess(sol, profile, tenant_id, target_contractor_id)
        except Exception as e:  # noqa: BLE001
            sol.pipeline_status = PipelineStatus.FAILED.value
            await db.commit()
            log.error("wph_pipeline_error", solicitation_id=str(solicitation_id), error=str(e))
            raise

        return {
            "solicitation_id": str(solicitation_id),
            "pipeline_status": sol.pipeline_status,
            "signal_count": sol.signal_count,
            "profile_id": str(profile.id),
            "alignment_count": len(alignments),
            "recommendation": assessment.recommendation if assessment else None,
            "pdq_score": assessment.pdq_score if assessment else None,
        }
