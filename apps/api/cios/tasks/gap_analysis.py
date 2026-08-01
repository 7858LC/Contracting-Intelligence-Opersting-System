"""Capability gap analysis task.

Turns an opportunity's Winning Profile alignment for the tenant's own
("self") contractor into persisted CapabilityGap rows — the tenant's
actionable, opportunity-specific view of what's standing between them and
the winning profile, with the WPH engine's already-computed closure plan
(action type, effort, timeline, feasibility, cost band) attached as a
remediation option.

No Claude call here: WPHAlignment.gaps and .gap_closures are already the
AI-derived output of the WPH engine (AlignmentScorer / GapCloser in
wph/alignment.py) that ran when Winning Profile alignment was generated.
Re-deriving them with a second Claude call would be redundant AI work over
the same evidence — this task is a pure DB read/compute over already-
computed rows, same reasoning as tasks/competitive_intel.py.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import structlog

from cios.tasks import celery_app

log = structlog.get_logger(__name__)

# GapCloser's cost_band ($/$$/$$$) is a relative tier, not a real quote —
# this is a documented, order-of-magnitude midpoint per tier so the UI has
# *something* to sort/roll up on. The authoritative, auditable figure stays
# the cost_band string itself, carried verbatim in remediation_options.
_COST_BAND_ESTIMATE = {"$": 15_000.0, "$$": 60_000.0, "$$$": 150_000.0}


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30, soft_time_limit=60)
def run_capability_gap_analysis(
    self, tenant_id: str, user_id: str, opportunity_id: str, run_id: str
) -> dict:
    try:
        return asyncio.run(_run_async(tenant_id, opportunity_id, run_id))
    except Exception as exc:
        log.error("capability_gap_analysis_failed", run_id=run_id, error=str(exc))
        raise self.retry(exc=exc)


async def _run_async(tenant_id: str, opportunity_id: str, run_id: str) -> dict:
    from sqlalchemy import select, text

    from cios.core.database import async_session_factory
    from cios.models.capability import CapabilityGap, CapabilityGapAnalysisRun
    from cios.models.winning_profile import WPHAlignment, WPHContractor, WPHProfile, WPHSolicitation

    async with async_session_factory() as db:
        # capability_gap_analysis_runs, capability_gaps, and wph_* all FORCE
        # ROW LEVEL SECURITY — this task runs outside the request lifecycle
        # on its own session, so without this every query below silently
        # returns zero rows instead of a real "not found."
        await db.execute(
            text("SELECT set_config('app.current_tenant', :tenant_id, false)"),
            {"tenant_id": tenant_id},
        )

        run = await db.get(CapabilityGapAnalysisRun, uuid.UUID(run_id))
        if not run:
            return {"error": "run record not found"}

        async def _fail(message: str) -> dict:
            run.status = "failed"
            run.error_message = message
            await db.commit()
            return {"run_id": run_id, "status": "failed", "error": message}

        sol = (
            await db.execute(
                select(WPHSolicitation).where(
                    WPHSolicitation.opportunity_id == uuid.UUID(opportunity_id),
                    WPHSolicitation.tenant_id == uuid.UUID(tenant_id),
                )
            )
        ).scalar_one_or_none()
        if not sol:
            return await _fail(
                "No Winning Profile solicitation linked to this opportunity yet — "
                "run Winning Profile analysis first."
            )

        profile = (
            await db.execute(
                select(WPHProfile).where(
                    WPHProfile.solicitation_id == sol.id, WPHProfile.is_current.is_(True)
                )
            )
        ).scalar_one_or_none()
        if not profile:
            return await _fail("No winning profile generated yet for this solicitation.")

        self_contractor = (
            await db.execute(
                select(WPHContractor)
                .where(
                    WPHContractor.tenant_id == uuid.UUID(tenant_id),
                    WPHContractor.is_self.is_(True),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if not self_contractor:
            return await _fail(
                "No contractor marked as your own org in Winning Profile yet — "
                "add and score your own org as a contractor first."
            )

        alignment = (
            await db.execute(
                select(WPHAlignment).where(
                    WPHAlignment.profile_id == profile.id,
                    WPHAlignment.contractor_id == self_contractor.id,
                )
            )
        ).scalar_one_or_none()
        if not alignment:
            return await _fail(
                "Your org hasn't been scored against this solicitation's winning profile "
                "yet — run contractor alignment first."
            )

        closures_by_attr = {c["gap_attribute_key"]: c for c in (alignment.gap_closures or [])}

        # Superseding a prior run's gaps for this opportunity rather than
        # accumulating duplicates on every re-analysis — deletion happens in
        # the same transaction as the new inserts below, so a mid-run
        # failure rolls back to the previous run's data intact.
        await db.execute(
            text(
                "DELETE FROM capability_gaps WHERE tenant_id = :tenant_id "
                "AND opportunity_id = :opportunity_id"
            ),
            {"tenant_id": tenant_id, "opportunity_id": opportunity_id},
        )

        gap_count = 0
        for gap in alignment.gaps or []:
            closure = closures_by_attr.get(gap["attribute_key"])
            remediation_options = [closure] if closure else []
            teaming_recommendation = (
                closure["recommendation"]
                if closure and closure["action_type"] in ("teaming", "partner")
                else None
            )
            estimated_time_to_close_days = (
                closure["timeline_months"] * 30 if closure else None
            )
            estimated_cost_to_close = (
                _COST_BAND_ESTIMATE.get(closure["cost_band"]) if closure else None
            )

            db.add(
                CapabilityGap(
                    tenant_id=uuid.UUID(tenant_id),
                    analysis_run_id=run.id,
                    opportunity_id=opportunity_id,
                    gap_name=gap["attribute_name"],
                    category=gap["category"],
                    severity=gap["severity"],
                    description=gap["impact"],
                    remediation_options=remediation_options,
                    estimated_cost_to_close=estimated_cost_to_close,
                    estimated_time_to_close_days=estimated_time_to_close_days,
                    teaming_recommendation=teaming_recommendation,
                    status="open",
                    evidence={
                        "attribute_key": gap["attribute_key"],
                        "required_level": gap["required_level"],
                        "contractor_level": gap["contractor_level"],
                        "gap_size": gap["gap_size"],
                        "importance_weight": gap["importance_weight"],
                        "solicitation_id": str(sol.id),
                        "profile_id": str(profile.id),
                        "contractor_id": str(self_contractor.id),
                        "source": "wph_alignment",
                    },
                    confidence_score=profile.overall_confidence / 100.0
                    if profile.overall_confidence
                    else None,
                    ai_model_version=profile.model_used,
                )
            )
            gap_count += 1

        run.status = "completed"
        run.solicitation_id = sol.id
        run.gap_count = gap_count
        run.generated_at = datetime.now(UTC)
        await db.commit()

    return {"run_id": run_id, "status": "completed", "gap_count": gap_count}
