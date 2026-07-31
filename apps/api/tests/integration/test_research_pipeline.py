"""End-to-end proof for cios/tasks/research.py's version of the same
idle-in-transaction bug fixed in tasks/analysis.py — see
test_opportunity_analysis_pipeline.py for the full account of the
production failure this class of bug caused.

This task had the worst-case shape of the three: one session spanning a
loop over every tracked agency, each iteration doing an external
USASpending HTTP call and then a real Claude call (Director-tier, easily
minutes) via ResearchAnalystAgent — and nothing committed until every
agency (and the final report) had been processed. A connection death
anywhere in that loop lost the *entire* brief, including agencies that had
already succeeded, since none of their work had actually been written yet.

Mocks USASpendingScanner.aggregate_agency_period (external HTTP, unrelated
to either bug here) and BaseAgent._call_claude. Everything else — the
AgencyProfile/AgencyBuyingPattern/ResearchReport rows, the real async
pipeline — runs against the real test database. research_reports and its
siblings are deliberately not tenant-scoped (see cios/models/research.py),
so unlike the other pipeline tests there's no app.current_tenant to set.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import event as sa_event
from sqlalchemy import select

from cios.agents.base import BaseAgent
from cios.core.database import async_session_factory
from cios.models.research import AgencyBuyingPattern, AgencyProfile, ResearchReport
from cios.scanners.usaspending import USASpendingScanner

_BRIEF_JSON = """```json
{
  "executive_summary": "Steady award activity concentrated in IT services this quarter.",
  "key_findings": ["Top NAICS code accounts for a plurality of sampled spend"],
  "priority_sectors": [{"naics": "541512", "rationale": "Largest sampled obligation"}],
  "capture_implications": "Prioritize teaming on the top NAICS code.",
  "data_limitations": "Bounded top-award sample, not a complete total.",
  "confidence_explanation": "Moderate confidence given sample size."
}
```"""

_AGGREGATE = {
    "total_obligated_amount": 12_500_000.0,
    "award_count": 4,
    "top_naics_breakdown": {"541512": 8_000_000.0},
    "source_evidence": [{"source": "usaspending", "note": "sampled top awards"}],
    "errors": [],
}


async def _deactivate_all_agencies() -> None:
    """agency_profiles is deliberately not tenant-scoped (see
    cios/models/research.py), so unlike every other table in this suite
    there's no RLS boundary isolating one test's rows from another's — a
    prior test's still-active agency would otherwise get swept into this
    test's call to _async_generate_brief, which queries every active row
    with no filter of its own. Called before seeding each test's own
    agencies so the task only ever sees what that test intends."""
    async with async_session_factory() as db:
        agencies = (await db.execute(select(AgencyProfile))).scalars().all()
        for agency in agencies:
            agency.is_active = False
        await db.commit()


async def _seed_agency(name_suffix: str) -> str:
    async with async_session_factory() as db:
        agency = AgencyProfile(
            name=f"Test Agency {name_suffix}",
            usaspending_toptier_code="097",
            is_active=True,
        )
        db.add(agency)
        await db.commit()
        return str(agency.id)


@pytest.mark.anyio
async def test_research_brief_populates_pattern_and_report_from_fenced_claude_output():
    from cios.tasks.research import _async_generate_brief

    await _deactivate_all_agencies()
    agency_id = await _seed_agency(uuid.uuid4().hex[:8])

    with (
        patch.object(
            USASpendingScanner,
            "aggregate_agency_period",
            new=AsyncMock(return_value=_AGGREGATE),
        ),
        patch.object(BaseAgent, "_call_claude", new=AsyncMock(return_value=_BRIEF_JSON)),
    ):
        result = await _async_generate_brief(period_label="2099-Q1-test")

    assert result["report_id"]
    assert result["errors"] == []

    async with async_session_factory() as db:
        pattern = (
            await db.execute(
                select(AgencyBuyingPattern).where(
                    AgencyBuyingPattern.agency_id == uuid.UUID(agency_id)
                )
            )
        ).scalar_one()
        assert pattern.total_obligated_amount == 12_500_000.0
        assert pattern.award_count == 4

        report = (
            await db.execute(
                select(ResearchReport).where(ResearchReport.id == uuid.UUID(result["report_id"]))
            )
        ).scalar_one()
        assert report.summary is not None
        assert "IT services" in report.summary


@pytest.mark.anyio
async def test_research_brief_holds_no_db_connection_across_the_claude_call():
    """Tracked via engine-level checkout/checkin events rather than
    pool.checkedout() — see test_opportunity_analysis_pipeline.py's
    identical test for why: that accessor only exists on QueuePool (what
    this suite gets without CIOS_WORKER_PROCESS set) and raises
    AttributeError on NullPool (what the production worker actually uses),
    while the events fire identically on both.
    """
    from cios.core.database import engine
    from cios.tasks.research import _async_generate_brief

    await _deactivate_all_agencies()
    await _seed_agency(uuid.uuid4().hex[:8])

    sync_engine = engine.sync_engine
    active = [0]
    checkouts_during_claude_call: list[int] = []

    def _on_checkout(*_args: object) -> None:
        active[0] += 1

    def _on_checkin(*_args: object) -> None:
        active[0] -= 1

    async def fake_call_claude(*args, **kwargs) -> str:
        checkouts_during_claude_call.append(active[0])
        return _BRIEF_JSON

    sa_event.listen(sync_engine, "checkout", _on_checkout)
    sa_event.listen(sync_engine, "checkin", _on_checkin)
    try:
        with (
            patch.object(
                USASpendingScanner,
                "aggregate_agency_period",
                new=AsyncMock(return_value=_AGGREGATE),
            ),
            patch.object(BaseAgent, "_call_claude", new=AsyncMock(side_effect=fake_call_claude)),
        ):
            result = await _async_generate_brief(period_label="2099-Q2-test")
    finally:
        sa_event.remove(sync_engine, "checkout", _on_checkout)
        sa_event.remove(sync_engine, "checkin", _on_checkin)

    assert checkouts_during_claude_call, "the mocked Claude call never ran"
    assert max(checkouts_during_claude_call) == 0, (
        "task held a pooled DB connection while waiting on Claude "
        f"(samples {checkouts_during_claude_call})"
    )
    assert result["report_id"]


@pytest.mark.anyio
async def test_research_brief_survives_one_agency_failing():
    """A later agency's Claude call failing must not lose an earlier
    agency's already-committed AgencyBuyingPattern — the whole point of
    committing per-agency instead of once at the very end. Before the fix,
    nothing committed until the full loop (and the report) finished, so any
    failure anywhere lost everything, not just that one agency's section.
    """
    from cios.tasks.research import _async_generate_brief

    await _deactivate_all_agencies()
    good_agency_id = await _seed_agency("good-" + uuid.uuid4().hex[:8])
    bad_agency_id = await _seed_agency("bad-" + uuid.uuid4().hex[:8])

    async def fake_aggregate(*, agency_name: str, **kwargs) -> dict:
        if "bad-" in agency_name:
            raise RuntimeError("USASpending request failed")
        return _AGGREGATE

    with (
        patch.object(
            USASpendingScanner, "aggregate_agency_period", new=AsyncMock(side_effect=fake_aggregate)
        ),
        patch.object(BaseAgent, "_call_claude", new=AsyncMock(return_value=_BRIEF_JSON)),
    ):
        result = await _async_generate_brief(period_label="2099-Q3-test")

    assert any("USASpending request failed" in e for e in result["errors"])
    assert len(result["agencies_covered"]) == 1

    async with async_session_factory() as db:
        good_pattern = (
            await db.execute(
                select(AgencyBuyingPattern).where(
                    AgencyBuyingPattern.agency_id == uuid.UUID(good_agency_id)
                )
            )
        ).scalar_one_or_none()
        assert good_pattern is not None
        assert good_pattern.total_obligated_amount == 12_500_000.0

        bad_pattern = (
            await db.execute(
                select(AgencyBuyingPattern).where(
                    AgencyBuyingPattern.agency_id == uuid.UUID(bad_agency_id)
                )
            )
        ).scalar_one_or_none()
        assert bad_pattern is None
