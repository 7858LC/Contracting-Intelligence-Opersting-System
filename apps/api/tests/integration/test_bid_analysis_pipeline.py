"""End-to-end proof for the PDQ (Bid/No-Bid Engine) bug reported live: a
decision showed "Analyzed" with every score and the recommendation blank.

Mocks only the Claude call itself (BaseAgent._call_claude), with the exact
response shape that broke this before the fix — JSON wrapped in a ```json
fence, which is Claude's routine behavior despite "no markdown" system
prompt instructions. Everything else (tenant, opportunity, BidDecision row,
the real async pipeline in tasks/bid_analysis.py) runs against the real
test database, the same as the rest of this test tier.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select, text

from cios.agents.base import BaseAgent
from cios.core.database import async_session_factory
from cios.models.bid_decision import BidDecision
from cios.models.opportunity import Opportunity
from cios.models.tenant import Tenant


async def _set_tenant(db, tenant_id) -> None:
    await db.execute(
        text("SELECT set_config('app.current_tenant', :t, false)"), {"t": str(tenant_id)}
    )

_CAPTURE_JSON = """```json
{
  "strategic_fit_score": 82,
  "win_probability_score": 68,
  "past_performance_score": 74,
  "capability_match_score": 71,
  "bid_no_bid_recommendation": "BID",
  "recommendation_rationale": "Strong strategic fit and incumbent-adjacent past performance.",
  "confidence_score": 0.78
}
```"""

_RISK_JSON = """```json
{
  "risk_score": 35,
  "risks": [
    {"description": "Aggressive timeline relative to typical proposal cycles.",
     "severity": "medium"}
  ]
}
```"""


async def _fake_call_claude(system_prompt: str, *args, **kwargs) -> str:
    # patch.object(BaseAgent, "_call_claude", new=AsyncMock(...)) replaces the
    # class attribute directly — accessing it via `self._call_claude(...)`
    # does NOT bind `self` the way a real method's descriptor protocol would,
    # so this side_effect receives exactly the positional args the caller
    # passed (system_prompt, user_message, ...), with no leading self.
    if "Risk Director" in system_prompt:
        return _RISK_JSON
    return _CAPTURE_JSON


@pytest.mark.anyio
async def test_bid_analysis_populates_real_scores_from_fenced_claude_output():
    from cios.tasks.bid_analysis import _run_async

    async with async_session_factory() as db:
        tenant = Tenant(name="Bid Analysis Test", slug=f"bid-analysis-test-{uuid.uuid4().hex[:8]}")
        db.add(tenant)
        await db.flush()
        await _set_tenant(db, tenant.id)

        opp = Opportunity(
            tenant_id=tenant.id,
            title="Bid Analysis Test Opportunity",
            agency="Test Agency",
            source="manual",
        )
        db.add(opp)
        await db.flush()

        decision = BidDecision(
            tenant_id=tenant.id,
            opportunity_id=opp.id,
            created_by=uuid.uuid4(),
            scoring_weights={
                "strategic_fit": 0.3,
                "win_probability": 0.3,
                "past_performance": 0.2,
                "capability_match": 0.1,
                "risk": 0.1,
            },
        )
        db.add(decision)
        await db.commit()
        decision_id = str(decision.id)
        tenant_id = str(tenant.id)

    # _run_async must set its own app.current_tenant — it must not rely on
    # inheriting it from whatever a previous session left on the pooled
    # physical connection. Clearing it here on a session that's likely to
    # share that connection is what makes this test actually exercise that,
    # instead of silently passing on leaked pool state the way this test did
    # before the fix (see cios/core/database.py's module docstring for why
    # that leakage happens and why CIOS_WORKER_PROCESS uses NullPool instead).
    async with async_session_factory() as db:
        await _set_tenant(db, uuid.UUID("00000000-0000-0000-0000-000000000000"))

    with patch.object(BaseAgent, "_call_claude", new=AsyncMock(side_effect=_fake_call_claude)):
        result = await _run_async(tenant_id, str(uuid.uuid4()), decision_id)

    assert result["status"] == "completed"

    async with async_session_factory() as db:
        await _set_tenant(db, uuid.UUID(tenant_id))
        row = (
            await db.execute(select(BidDecision).where(BidDecision.id == uuid.UUID(decision_id)))
        ).scalar_one()

        # This is exactly what was missing before the fix: every one of
        # these silently stayed None/[] while analyzed_at was set anyway.
        assert row.analyzed_at is not None
        assert row.strategic_fit_score == 82
        assert row.win_probability_score == 68
        assert row.risk_score == 35
        assert row.recommendation == "BID"
        assert row.recommendation_rationale is not None
        assert "strategic fit" in row.recommendation_rationale
        assert row.risks and row.risks[0]["description"].startswith("Aggressive timeline")
        assert row.composite_score is not None


@pytest.mark.anyio
async def test_bid_analysis_holds_no_db_connection_across_the_claude_calls():
    """Same invariant as the opportunity pipeline's version of this test, for
    the same reason — see test_opportunity_analysis_pipeline.py for the full
    account of the production failure.

    This task never had that failure attributed to it, but it had the identical
    shape: two Director calls of ~130-180s each of pure external HTTP wrapped
    in one session whose transaction stayed open the whole time. That parks the
    connection idle-in-transaction for minutes, which managed Postgres hosts
    drop, surfacing only at the deferred commit as "connection is closed". The
    window was shorter than the opportunity task's, which is the only reason it
    hadn't been observed yet.

    Tracked via engine-level checkout/checkin events rather than
    pool.checkedout() — see test_opportunity_analysis_pipeline.py's identical
    test for why: that accessor only exists on QueuePool (what this suite
    gets without CIOS_WORKER_PROCESS set) and raises AttributeError on
    NullPool (what the production worker actually uses, and what this test
    gets when run with CIOS_WORKER_PROCESS=1 to match it), while the events
    fire identically on both.
    """
    from sqlalchemy import event as sa_event

    from cios.core.database import engine
    from cios.tasks.bid_analysis import _run_async

    sync_engine = engine.sync_engine
    active = [0]
    checkouts_during_claude_calls: list[int] = []

    def _on_checkout(*_args: object) -> None:
        active[0] += 1

    def _on_checkin(*_args: object) -> None:
        active[0] -= 1

    async with async_session_factory() as db:
        tenant = Tenant(
            name="Bid Analysis Idle Txn Test", slug=f"bid-analysis-idletxn-{uuid.uuid4().hex[:8]}"
        )
        db.add(tenant)
        await db.flush()
        await _set_tenant(db, tenant.id)

        opp = Opportunity(
            tenant_id=tenant.id,
            title="Bid Analysis Idle Txn Test Opportunity",
            agency="Test Agency",
            source="manual",
        )
        db.add(opp)
        await db.flush()

        decision = BidDecision(
            tenant_id=tenant.id,
            opportunity_id=opp.id,
            created_by=uuid.uuid4(),
            scoring_weights={"strategic_fit": 0.5, "win_probability": 0.5},
        )
        db.add(decision)
        await db.commit()
        decision_id = str(decision.id)
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
        return await _fake_call_claude(system_prompt, *args, **kwargs)

    try:
        with patch.object(BaseAgent, "_call_claude", new=AsyncMock(side_effect=fake_call_claude)):
            result = await _run_async(tenant_id, str(uuid.uuid4()), decision_id)
    finally:
        sa_event.remove(sync_engine, "checkout", _on_checkout)
        sa_event.remove(sync_engine, "checkin", _on_checkin)

    assert checkouts_during_claude_calls, "the mocked Claude call never ran"
    assert max(checkouts_during_claude_calls) == 0, (
        "task held a pooled DB connection while waiting on Claude "
        f"(samples {checkouts_during_claude_calls})"
    )
    assert result["status"] == "completed"

    async with async_session_factory() as db:
        await _set_tenant(db, uuid.UUID(tenant_id))
        row = (
            await db.execute(select(BidDecision).where(BidDecision.id == uuid.UUID(decision_id)))
        ).scalar_one()
        assert row.analyzed_at is not None
        assert row.strategic_fit_score == 82
        assert row.recommendation == "BID"


_CAPTURE_JSON_NESTED_RECOMMENDATION = """```json
{
  "strategic_fit_score": 55,
  "win_probability_score": 40,
  "past_performance_score": 60,
  "capability_match_score": 58,
  "bid_no_bid_recommendation": {
    "recommendation": "CONDITIONAL — DEFER pending teaming partner confirmation",
    "confidence": "medium"
  },
  "recommendation_rationale": "Borderline fit; needs a subcontractor for the cyber requirement.",
  "confidence_score": 0.5
}
```"""


@pytest.mark.anyio
async def test_bid_analysis_survives_nested_recommendation_object():
    """Reproduces the live failure: DataError('invalid input for query
    argument $1: {...} (expected str, got dict)') when Claude nests the
    recommendation and its rationale/confidence into one JSON object instead
    of the flat string the "bid_no_bid_recommendation" column expects. Before
    the fix this crashed the whole write, so every other score in the same
    commit — none of which were the problem — was lost right along with it.
    """
    from cios.tasks.bid_analysis import _run_async

    async def fake_call_claude(system_prompt: str, *args, **kwargs) -> str:
        if "Risk Director" in system_prompt:
            return _RISK_JSON
        return _CAPTURE_JSON_NESTED_RECOMMENDATION

    async with async_session_factory() as db:
        tenant = Tenant(
            name="Bid Analysis Nested Rec Test",
            slug=f"bid-analysis-nested-rec-{uuid.uuid4().hex[:8]}",
        )
        db.add(tenant)
        await db.flush()
        await _set_tenant(db, tenant.id)

        opp = Opportunity(
            tenant_id=tenant.id,
            title="Bid Analysis Nested Rec Test Opportunity",
            agency="Test Agency",
            source="manual",
        )
        db.add(opp)
        await db.flush()

        decision = BidDecision(
            tenant_id=tenant.id,
            opportunity_id=opp.id,
            created_by=uuid.uuid4(),
            scoring_weights={"strategic_fit": 0.3, "win_probability": 0.3, "risk": 0.4},
        )
        db.add(decision)
        await db.commit()
        decision_id = str(decision.id)
        tenant_id = str(tenant.id)

    async with async_session_factory() as db:
        await _set_tenant(db, uuid.UUID("00000000-0000-0000-0000-000000000000"))

    with patch.object(BaseAgent, "_call_claude", new=AsyncMock(side_effect=fake_call_claude)):
        result = await _run_async(tenant_id, str(uuid.uuid4()), decision_id)

    assert result["status"] == "completed"

    async with async_session_factory() as db:
        await _set_tenant(db, uuid.UUID(tenant_id))
        row = (
            await db.execute(select(BidDecision).where(BidDecision.id == uuid.UUID(decision_id)))
        ).scalar_one()

        assert row.analyzed_at is not None
        # The nested object couldn't be coerced to a known field, so this
        # falls back to None rather than crashing — but every other score in
        # the same commit, which the nested shape had nothing to do with,
        # must still land.
        assert row.recommendation is None
        assert row.strategic_fit_score == 55
        assert row.risk_score == 35
        assert row.composite_score is not None
