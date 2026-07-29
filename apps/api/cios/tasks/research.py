"""Research module Celery tasks — Agency Intelligence Brief generation.

Phase 1 of the Executive Council research pipeline. Deliberately reads only
platform-owned, public-data-derived tables (cios/models/research.py) — never
touches any tenant's data, consistent with that module's tenant-isolation
exception being the other direction (public data made available to every
Council-member tenant, not tenant data made available platform-wide).

Report content is stored directly in research_reports.content (JSONB) rather
than rendered to a file and uploaded to S3 — no object-storage account
needed at this scale (a handful of small quarterly reports).
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select

from cios.tasks import celery_app

log = structlog.get_logger(__name__)


def _run(coro):  # noqa: ANN001, ANN201
    return asyncio.run(coro)


@celery_app.task(
    name="cios.tasks.research.generate_agency_intelligence_brief",
    queue="research",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
)
def generate_agency_intelligence_brief(self, period_label: str | None = None) -> dict:
    """Generate one quarter's Agency Intelligence Brief covering every active
    AgencyProfile. period_label defaults to the current quarter (e.g. "2026-Q3")."""
    try:
        return _run(_async_generate_brief(period_label))
    except Exception as exc:
        log.error("agency_brief_generation_failed", error=str(exc))
        raise self.retry(exc=exc)


def _current_quarter_label(now: datetime) -> tuple[str, datetime, datetime]:
    quarter = (now.month - 1) // 3 + 1
    start_month = (quarter - 1) * 3 + 1
    period_start = datetime(now.year, start_month, 1, tzinfo=UTC)
    end_month = start_month + 2
    if end_month == 12:
        period_end = datetime(now.year, 12, 31, tzinfo=UTC)
    else:
        next_month_first = datetime(now.year, end_month + 1, 1, tzinfo=UTC)
        period_end = next_month_first
    return f"{now.year}-Q{quarter}", period_start, period_end


async def _async_generate_brief(period_label: str | None) -> dict:
    from cios.agents.base import AgentContext
    from cios.agents.research_analyst_agent import ResearchAnalystAgent
    from cios.core.database import async_session_factory
    from cios.models.research import (
        AgencyBuyingPattern,
        AgencyProfile,
        ReportStatus,
        ResearchReport,
    )
    from cios.scanners.usaspending import USASpendingScanner

    # Only current-quarter generation is supported for now; an explicit
    # period_label is accepted purely as a label override for testing/backfill,
    # the date range itself always follows the current quarter until this task
    # gains real historical-period support.
    now = datetime.now(UTC)
    label, period_start, period_end = _current_quarter_label(now)
    if period_label:
        label = period_label

    async with async_session_factory() as db:
        agencies = (
            (await db.execute(select(AgencyProfile).where(AgencyProfile.is_active == True)))  # noqa: E712
            .scalars()
            .all()
        )
        if not agencies:
            return {"error": "No active AgencyProfile rows — seed DoD/GSA/VA first"}

        sections: list[dict] = []
        errors: list[str] = []

        async with USASpendingScanner() as scanner:
            for agency in agencies:
                try:
                    aggregate = await scanner.aggregate_agency_period(
                        agency_name=agency.name,
                        period_start=period_start,
                        period_end=period_end,
                    )
                    errors.extend(aggregate.get("errors", []))

                    # Rerunning generation for a period already covered (e.g. a
                    # retry after fixing a bad query) must refresh the existing
                    # row rather than insert a duplicate — uq_agency_period
                    # enforces one row per (agency, period).
                    pattern = (
                        await db.execute(
                            select(AgencyBuyingPattern).where(
                                AgencyBuyingPattern.agency_id == agency.id,
                                AgencyBuyingPattern.period_start == period_start,
                                AgencyBuyingPattern.period_end == period_end,
                            )
                        )
                    ).scalar_one_or_none()
                    if pattern is None:
                        pattern = AgencyBuyingPattern(
                            agency_id=agency.id,
                            period_start=period_start,
                            period_end=period_end,
                        )
                        db.add(pattern)
                    pattern.total_obligated_amount = aggregate["total_obligated_amount"]
                    pattern.award_count = aggregate["award_count"]
                    pattern.recompete_count = 0  # TODO: needs same-PIID-base award history tracking
                    pattern.top_naics_breakdown = aggregate["top_naics_breakdown"]
                    pattern.source_evidence = aggregate["source_evidence"]

                    agent = ResearchAnalystAgent()
                    ctx = AgentContext(tenant_id=uuid.uuid4(), user_id=uuid.uuid4())
                    run = await agent.run(
                        ctx,
                        agency_name=agency.name,
                        period_label=label,
                        period_start=period_start.date().isoformat(),
                        period_end=period_end.date().isoformat(),
                        aggregate=aggregate,
                    )
                    sections.append({"agency": agency.name, "brief": run["result"]})
                except Exception as e:
                    errors.append(f"{agency.name}: {e}")
                    log.warning("agency_brief_section_failed", agency=agency.name, error=str(e))

        if not sections:
            return {"error": "All agency sections failed", "errors": errors}

        report = ResearchReport(
            report_type="agency_intelligence_brief",
            period_label=label,
            status=ReportStatus.PUBLISHED.value,
            title=f"Agency Intelligence Brief — {label}",
            summary=sections[0]["brief"]["executive_summary"] if sections else None,
            content=sections,
            published_at=now,
        )
        db.add(report)
        await db.commit()

        return {
            "report_id": str(report.id),
            "period_label": label,
            "agencies_covered": [s["agency"] for s in sections],
            "errors": errors,
        }
