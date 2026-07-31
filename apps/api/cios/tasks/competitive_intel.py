"""Competitive intelligence analysis task.

Turns a solicitation's WPH alignment ranking into a competitive landscape:
who's the front-runner (highest-ranked non-self contractor), who's in the
next tiers, each enriched with the tenant's tracked Competitor intel where
a link exists (WPHContractor.competitor_id — see migration 020 and
winning_profile.py's create_contractor/link_contractor_competitor for how
that link gets set). A contractor ranked but not yet linked to a Competitor
gets one auto-created here, seeded from its WPH identity fields, so the
landscape is never missing tracked intel purely because nobody manually
linked it first.

No Claude call in this task — it's a pure DB read/compute over already-
computed WPHAlignment rows, so none of the idle-in-transaction/session-
splitting concerns from tasks/analysis.py and friends apply here.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import structlog

from cios.tasks import celery_app

log = structlog.get_logger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30, soft_time_limit=60)
def run_competitive_analysis(
    self, tenant_id: str, user_id: str, opportunity_id: str, analysis_id: str
) -> dict:
    try:
        return asyncio.run(_run_async(tenant_id, opportunity_id, analysis_id))
    except Exception as exc:
        log.error("competitive_analysis_failed", analysis_id=analysis_id, error=str(exc))
        raise self.retry(exc=exc)


async def _run_async(tenant_id: str, opportunity_id: str, analysis_id: str) -> dict:
    from sqlalchemy import select, text

    from cios.core.database import async_session_factory
    from cios.models.competitor import CompetitiveLandscapeAnalysis, Competitor
    from cios.models.winning_profile import WPHAlignment, WPHContractor, WPHProfile, WPHSolicitation

    async with async_session_factory() as db:
        # competitive_landscape_analyses, competitors, and wph_* all FORCE
        # ROW LEVEL SECURITY — this task runs outside the request lifecycle
        # on its own session, so without this every query below silently
        # returns zero rows instead of a real "not found."
        await db.execute(
            text("SELECT set_config('app.current_tenant', :tenant_id, false)"),
            {"tenant_id": tenant_id},
        )

        analysis = await db.get(CompetitiveLandscapeAnalysis, uuid.UUID(analysis_id))
        if not analysis:
            return {"error": "analysis record not found"}

        async def _fail(message: str) -> dict:
            analysis.status = "failed"
            analysis.error_message = message
            await db.commit()
            return {"analysis_id": analysis_id, "status": "failed", "error": message}

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

        alignments = (
            (
                await db.execute(
                    select(WPHAlignment)
                    .where(WPHAlignment.profile_id == profile.id)
                    .order_by(WPHAlignment.rank.asc())
                )
            )
            .scalars()
            .all()
        )
        if not alignments:
            return await _fail("No contractors aligned yet — run alignment first.")

        contractor_rows = (
            (
                await db.execute(
                    select(WPHContractor).where(
                        WPHContractor.id.in_([a.contractor_id for a in alignments])
                    )
                )
            )
            .scalars()
            .all()
        )
        contractors_by_id = {c.id: c for c in contractor_rows}

        def _is_self(alignment) -> bool:  # noqa: ANN001
            contractor = contractors_by_id.get(alignment.contractor_id)
            return bool(contractor and contractor.is_self)

        ranked = [a for a in alignments if not _is_self(a)]
        if not ranked:
            return await _fail(
                "Only your own org is scored for this solicitation — add competitor "
                "contractors in Winning Profile to see the competitive landscape."
            )

        enriched = []
        for a in ranked:
            contractor = contractors_by_id.get(a.contractor_id)
            competitor = None

            if contractor and contractor.competitor_id:
                competitor = await db.get(Competitor, contractor.competitor_id)

            if not competitor and contractor and contractor.cage_code:
                competitor = (
                    await db.execute(
                        select(Competitor).where(
                            Competitor.tenant_id == uuid.UUID(tenant_id),
                            Competitor.cage_code == contractor.cage_code,
                        )
                    )
                ).scalar_one_or_none()

            if not competitor and contractor:
                competitor = Competitor(
                    tenant_id=uuid.UUID(tenant_id),
                    company_name=contractor.name,
                    cage_code=contractor.cage_code,
                    naics_codes=contractor.naics_codes or [],
                    certifications=contractor.certifications or [],
                )
                db.add(competitor)
                await db.flush()

            if contractor and competitor and contractor.competitor_id != competitor.id:
                contractor.competitor_id = competitor.id

            enriched.append(
                {
                    "contractor_id": str(a.contractor_id),
                    "contractor_name": a.contractor_name,
                    "alignment_score": a.overall_alignment_score,
                    "rank": a.rank,
                    "competitor_id": str(competitor.id) if competitor else None,
                    "threat_level": competitor.threat_level if competitor else None,
                    "pricing_tendency": competitor.pricing_tendency if competitor else None,
                    "known_strengths": competitor.known_strengths if competitor else [],
                    "known_weaknesses": competitor.known_weaknesses if competitor else [],
                    "notes": competitor.notes if competitor else None,
                }
            )

        analysis.status = "completed"
        analysis.solicitation_id = sol.id
        analysis.front_runner = enriched[0]
        analysis.next_tiers = enriched[1:6]
        analysis.candidate_pool_size = len(enriched)
        analysis.generated_at = datetime.now(UTC)
        await db.commit()

    return {"analysis_id": analysis_id, "status": "completed"}
