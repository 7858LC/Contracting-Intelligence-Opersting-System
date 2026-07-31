"""End-to-end proof for the Opportunity Intelligence "Run AI Analysis" bug
reported live: the button queued a task, the toast promised results, and
nothing ever came back — no score, no error, nothing in the UI to explain
why. Root cause was tasks/analysis.py's _run_async never setting
app.current_tenant before querying `opportunities` (FORCE ROW LEVEL
SECURITY), so the SELECT silently returned zero rows and the task exited
early having written nothing — the exact same class of bug as
test_bid_analysis_pipeline.py, just never ported to this sibling task.

Mocks only the Claude call itself (BaseAgent._call_claude), with the exact
response shape that broke this before the fix — JSON wrapped in a ```json
fence, which is Claude's routine behavior despite "no markdown" system
prompt instructions. Everything else (tenant, opportunity row, the real
async pipeline in tasks/analysis.py, the real CEO + Director agent
orchestration) runs against the real test database, the same as the rest
of this test tier.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select, text

from cios.agents.base import BaseAgent
from cios.core.database import async_session_factory
from cios.models.opportunity import Opportunity
from cios.models.tenant import Tenant


async def _set_tenant(db, tenant_id) -> None:
    await db.execute(
        text("SELECT set_config('app.current_tenant', :t, false)"), {"t": str(tenant_id)}
    )


_CEO_JSON = """```json
{
  "gate_review_recommendation": "BID",
  "award_probability": 0.62,
  "confidence_score": 0.71,
  "strategic_recommendation": "Pursue — strong past performance overlap and a defensible approach.",
  "key_decision_factors": ["Incumbent has a mixed CPARS record", "Our set-aside eligibility"],
  "critical_risks": [
    {"risk": "Aggressive 30-day proposal turnaround.", "mitigation": "Start volume leads now."}
  ],
  "alternatives": ["Team with a past performance partner to backfill the one gap."],
  "regulation_citations": ["FAR 15.305"]
}
```"""


async def _fake_call_claude(system_prompt: str, *args, **kwargs) -> str:
    # patch.object(BaseAgent, "_call_claude", new=AsyncMock(...)) replaces the
    # class attribute directly — accessing it via `self._call_claude(...)`
    # does NOT bind `self` the way a real method's descriptor protocol would,
    # so this side_effect receives exactly the positional args the caller
    # passed (system_prompt, user_message, ...), with no leading self.
    if "Chief Intelligence Officer" in system_prompt:
        return _CEO_JSON
    # Director outputs only feed the CEO's evidence block as free text in
    # this task — they're never parsed as JSON here — so any non-empty
    # string exercises the real fan-out without needing five more fixtures.
    return "Director assessment: moderate confidence, no blocking issues identified."


@pytest.mark.anyio
async def test_opportunity_analysis_populates_real_scores_from_fenced_claude_output():
    from cios.tasks.analysis import _run_async

    async with async_session_factory() as db:
        tenant = Tenant(
            name="Opportunity Analysis Test", slug=f"opp-analysis-test-{uuid.uuid4().hex[:8]}"
        )
        db.add(tenant)
        await db.flush()
        await _set_tenant(db, tenant.id)

        opp = Opportunity(
            tenant_id=tenant.id,
            title="Opportunity Analysis Test Opportunity",
            agency="Test Agency",
            source="manual",
        )
        db.add(opp)
        await db.commit()
        opportunity_id = str(opp.id)
        tenant_id = str(tenant.id)

    # _run_async must set its own app.current_tenant — it must not rely on
    # inheriting it from whatever a previous session left on the pooled
    # physical connection. Clearing it here on a session that's likely to
    # share that connection is what makes this test actually exercise that
    # (see test_bid_analysis_pipeline.py and cios/core/database.py's module
    # docstring) instead of silently passing on leaked pool state — which is
    # exactly how the missing set_config call here went undetected.
    async with async_session_factory() as db:
        await _set_tenant(db, uuid.UUID("00000000-0000-0000-0000-000000000000"))

    with patch.object(BaseAgent, "_call_claude", new=AsyncMock(side_effect=_fake_call_claude)):
        result = await _run_async(tenant_id, str(uuid.uuid4()), opportunity_id)

    assert result["status"] == "completed"

    async with async_session_factory() as db:
        await _set_tenant(db, uuid.UUID(tenant_id))
        row = (
            await db.execute(select(Opportunity).where(Opportunity.id == uuid.UUID(opportunity_id)))
        ).scalar_one()

        # This is exactly what was missing before the fix: the row never got
        # touched at all (RLS made the SELECT return zero rows, so the task
        # returned {"error": "opportunity not found"} and committed nothing) —
        # Celery still reported the task as a clean SUCCESS either way.
        assert row.analyzed_at is not None
        assert row.award_probability_score == 0.62
        assert row.bid_no_bid_recommendation == "BID"
        assert row.confidence_score == 0.71
        assert row.ai_model_version is not None


@pytest.mark.anyio
async def test_opportunity_analysis_holds_no_db_connection_across_the_claude_calls():
    """The task must not hold a Postgres connection — least of all one inside
    an open transaction — while it waits on the Anthropic API.

    This is the third distinct way "Run AI Analysis" failed in production, and
    the one that survived both earlier fixes. orchestrate_full_assessment is
    minutes of external HTTP with no DB access; an AsyncSession autobegins a
    transaction on its first statement and holds it until commit, so wrapping
    the orchestration in one session parked the connection in
    state='idle in transaction' for that whole window. Managed Postgres hosts
    kill those, and the Python side doesn't notice until the deferred UPDATE
    at the end, which then failed with the reported
    "asyncpg InterfaceError: connection is closed" — after every Claude call
    had already been paid for. Parallelizing the Directors shortened that
    window but could not close it, which is why the bug outlived that fix.

    The invariant is asserted in-process via the engine's own checkout/checkin
    pool events, registered and removed within this test only: while the
    Claude calls are in flight the task must have checked out no connection at
    all. Deliberately NOT by scanning pg_stat_activity for idle-in-transaction
    backends — an earlier version of this test did that, and because the whole
    suite shares one database it both mistook other tests' sessions for this
    task's and (when it terminated them to emulate the host's reaper) broke
    them. Also deliberately NOT via pool.checkedout() — that only exists on
    QueuePool; this test file's own suite run doesn't set CIOS_WORKER_PROCESS,
    so it gets QueuePool, but the production worker (and this test run when
    CIOS_WORKER_PROCESS=1 is set to actually match it) uses NullPool, whose
    checkout/checkin *events* still fire — verified directly — even though
    NullPool exposes no checkedout() accessor at all (calling it raises
    AttributeError). Engine-level events work identically on both pool
    classes, so this test is meaningful in either environment. Against the
    single-session version this fails: the sampled count sits one above
    baseline for the entire orchestration.
    """
    from sqlalchemy import event as sa_event

    from cios.core.database import engine
    from cios.tasks.analysis import _run_async

    sync_engine = engine.sync_engine
    active = [0]
    checkouts_during_claude_calls: list[int] = []

    def _on_checkout(*_args: object) -> None:
        active[0] += 1

    def _on_checkin(*_args: object) -> None:
        active[0] -= 1

    async with async_session_factory() as db:
        tenant = Tenant(
            name="Opportunity Analysis Idle Txn Test",
            slug=f"opp-analysis-idletxn-{uuid.uuid4().hex[:8]}",
        )
        db.add(tenant)
        await db.flush()
        await _set_tenant(db, tenant.id)

        opp = Opportunity(
            tenant_id=tenant.id,
            title="Opportunity Analysis Idle Txn Test Opportunity",
            agency="Test Agency",
            source="manual",
        )
        db.add(opp)
        await db.commit()
        opportunity_id = str(opp.id)
        tenant_id = str(tenant.id)

    # Registered fresh for this test and removed in the finally below, so a
    # connection some earlier or concurrent test holds never pollutes this
    # test's count — only events fired after registration are seen at all.
    sa_event.listen(sync_engine, "checkout", _on_checkout)
    sa_event.listen(sync_engine, "checkin", _on_checkin)

    async def fake_call_claude(system_prompt: str, *args, **kwargs) -> str:
        # Sampled with no session of its own open, so the reading reflects
        # only what the task under test is holding at this instant.
        checkouts_during_claude_calls.append(active[0])
        if "Chief Intelligence Officer" in system_prompt:
            return _CEO_JSON
        return "Director assessment: moderate confidence, no blocking issues identified."

    try:
        with patch.object(BaseAgent, "_call_claude", new=AsyncMock(side_effect=fake_call_claude)):
            result = await _run_async(tenant_id, str(uuid.uuid4()), opportunity_id)
    finally:
        sa_event.remove(sync_engine, "checkout", _on_checkout)
        sa_event.remove(sync_engine, "checkin", _on_checkin)

    # Every Director call and the CEO synthesis must each have run with the
    # task holding no connection at all — one sample per Claude call, all
    # zero.
    assert checkouts_during_claude_calls, "the mocked Claude call never ran"
    assert max(checkouts_during_claude_calls) == 0, (
        "task held a pooled DB connection while waiting on Claude "
        f"(samples {checkouts_during_claude_calls})"
    )
    assert result["status"] == "completed"

    # The write must still land on a healthy connection opened after the
    # slow work, not on the one that was held open across it.
    async with async_session_factory() as db:
        await _set_tenant(db, uuid.UUID(tenant_id))
        row = (
            await db.execute(select(Opportunity).where(Opportunity.id == uuid.UUID(opportunity_id)))
        ).scalar_one()
        assert row.analyzed_at is not None
        assert row.award_probability_score == 0.62
        assert row.bid_no_bid_recommendation == "BID"


_CEO_JSON_OFF_SCHEMA = """```json
{
  "summary": "Some unrelated shape Claude might drift into.",
  "notes": "no expected keys at all"
}
```"""


@pytest.mark.anyio
async def test_opportunity_analysis_raises_on_schema_noncompliant_response():
    """A response that parses as JSON but matches none of the expected keys
    must not silently commit a row with every score null — before the fix,
    a bare `json.loads` + `except: parsed = {}` would swallow this into an
    "analyzed" opportunity with nothing on it. It must instead raise (via
    extract_claude_json's require_any_of guard), which is what lets the
    outer Celery task's self.retry() (see the task wrapper's try/except)
    actually fire instead of silently completing having written nothing."""
    from cios.tasks.analysis import _run_async

    async def fake_call_claude(system_prompt: str, *args, **kwargs) -> str:
        if "Chief Intelligence Officer" in system_prompt:
            return _CEO_JSON_OFF_SCHEMA
        return "Director assessment: no issues."

    async with async_session_factory() as db:
        tenant = Tenant(
            name="Opportunity Analysis Off-Schema Test",
            slug=f"opp-analysis-offschema-{uuid.uuid4().hex[:8]}",
        )
        db.add(tenant)
        await db.flush()
        await _set_tenant(db, tenant.id)

        opp = Opportunity(
            tenant_id=tenant.id,
            title="Opportunity Analysis Off-Schema Test Opportunity",
            agency="Test Agency",
            source="manual",
        )
        db.add(opp)
        await db.commit()
        opportunity_id = str(opp.id)
        tenant_id = str(tenant.id)

    async with async_session_factory() as db:
        await _set_tenant(db, uuid.UUID("00000000-0000-0000-0000-000000000000"))

    with patch.object(BaseAgent, "_call_claude", new=AsyncMock(side_effect=fake_call_claude)):
        with pytest.raises(ValueError, match="none of the expected keys"):
            await _run_async(tenant_id, str(uuid.uuid4()), opportunity_id)

    async with async_session_factory() as db:
        await _set_tenant(db, uuid.UUID(tenant_id))
        row = (
            await db.execute(select(Opportunity).where(Opportunity.id == uuid.UUID(opportunity_id)))
        ).scalar_one()
        assert row.analyzed_at is None
        assert row.award_probability_score is None
