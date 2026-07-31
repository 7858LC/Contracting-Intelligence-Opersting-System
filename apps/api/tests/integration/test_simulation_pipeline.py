"""End-to-end proof for cios/tasks/simulation.py's two bugs found in the
same proactive sweep that fixed tasks/analysis.py and tasks/bid_analysis.py:

1. _run_simulation_async never set app.current_tenant before querying
   `award_simulations` (FORCE ROW LEVEL SECURITY, migration 007), so the
   SELECT silently returned zero rows and the task exited early having
   written nothing — the same class of bug tasks/analysis.py shipped with.

2. agent.run() (a real Claude call, often minutes) ran inside the same
   DB session used for the initial read, holding a Postgres connection
   idle-in-transaction for the whole wait — the exact bug reproduced and
   fixed in tasks/analysis.py, present here with the same shape. The old
   except block also depended on that same possibly-dead connection to
   record the failure, so a connection death lost the failure record too.

Mocks only the Claude call (BaseAgent._call_claude) and the vector search
(TenantVectorStore.search, unrelated to either bug here). Everything else —
tenant, opportunity, simulation row, the real async pipeline — runs against
the real test database.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import event as sa_event
from sqlalchemy import select, text

from cios.agents.base import BaseAgent
from cios.core.database import async_session_factory
from cios.models.award_simulation import AwardSimulation
from cios.models.opportunity import Opportunity
from cios.models.tenant import Tenant


async def _set_tenant(db, tenant_id) -> None:
    await db.execute(
        text("SELECT set_config('app.current_tenant', :t, false)"), {"t": str(tenant_id)}
    )


_SIMULATION_JSON = """```json
{
  "technical_score": 78,
  "management_score": 72,
  "past_performance_score": 80,
  "price_competitiveness_score": 65,
  "compliance_score": 90,
  "risk_score": 30,
  "overall_score": 74,
  "award_probability": 0.55,
  "confidence_score": 0.7,
  "strengths": ["Strong technical narrative"],
  "weaknesses": ["Price is above the competitive range"],
  "significant_weaknesses": [],
  "deficiencies": [],
  "risks": [{"description": "Schedule risk on staffing ramp", "severity": "medium"}],
  "red_team_comments": ["Evaluators may question price realism"],
  "suggested_improvements": ["Tighten the price narrative"],
  "executive_summary": "Competitive but priced above the likely range.",
  "gate_review_recommendation": "CONDITIONAL_BID",
  "rule_citations": ["FAR 15.305"],
  "factor_ratings": {"technical": "Green/Acceptable"}
}
```"""


async def _create_tenant_opp_and_sim() -> tuple[str, str]:
    async with async_session_factory() as db:
        tenant = Tenant(
            name="Simulation Pipeline Test", slug=f"sim-pipeline-test-{uuid.uuid4().hex[:8]}"
        )
        db.add(tenant)
        await db.flush()
        await _set_tenant(db, tenant.id)

        opp = Opportunity(
            tenant_id=tenant.id,
            title="Simulation Pipeline Test Opportunity",
            agency="Test Agency",
            source="manual",
        )
        db.add(opp)
        await db.flush()

        sim = AwardSimulation(
            tenant_id=tenant.id,
            opportunity_id=opp.id,
            name="Test Simulation",
        )
        db.add(sim)
        await db.commit()
        return str(tenant.id), str(sim.id)


@pytest.mark.anyio
async def test_simulation_populates_real_scores_from_fenced_claude_output():
    """Also the regression test for the missing set_config call: before the
    fix, the very first query in the task (fetching the AwardSimulation row
    itself) silently returned zero rows under RLS, so this would have failed
    with {"error": "simulation not found"} instead of ever reaching Claude.
    """
    from cios.tasks.simulation import _run_simulation_async

    tenant_id, simulation_id = await _create_tenant_opp_and_sim()

    async def fake_call_claude(system_prompt: str, *args, **kwargs) -> str:
        return _SIMULATION_JSON

    with (
        patch.object(BaseAgent, "_call_claude", new=AsyncMock(side_effect=fake_call_claude)),
        patch(
            "cios.vector.tenant_store.TenantVectorStore.search",
            new=AsyncMock(return_value=[]),
        ),
    ):
        result = await _run_simulation_async(tenant_id, str(uuid.uuid4()), simulation_id, {})

    assert result["status"] == "completed"

    async with async_session_factory() as db:
        await _set_tenant(db, uuid.UUID(tenant_id))
        row = (
            await db.execute(
                select(AwardSimulation).where(AwardSimulation.id == uuid.UUID(simulation_id))
            )
        ).scalar_one()

        assert row.status == "completed"
        assert row.overall_score == 74
        assert row.gate_review_recommendation == "CONDITIONAL_BID"
        assert row.ai_model_version is not None


@pytest.mark.anyio
async def test_simulation_holds_no_db_connection_across_the_claude_call():
    """Same invariant as tasks/analysis.py's version of this test, for the
    same reason — see test_opportunity_analysis_pipeline.py for the full
    account of the production failure this class of bug caused. Tracked via
    engine-level checkout/checkin events rather than pool.checkedout(): that
    accessor only exists on QueuePool (what this suite gets without
    CIOS_WORKER_PROCESS set) and raises AttributeError on NullPool (what the
    production worker actually uses), while the events fire identically on
    both.
    """
    from cios.core.database import engine
    from cios.tasks.simulation import _run_simulation_async

    tenant_id, simulation_id = await _create_tenant_opp_and_sim()

    sync_engine = engine.sync_engine
    active = [0]
    checkouts_during_claude_call: list[int] = []

    def _on_checkout(*_args: object) -> None:
        active[0] += 1

    def _on_checkin(*_args: object) -> None:
        active[0] -= 1

    async def fake_call_claude(system_prompt: str, *args, **kwargs) -> str:
        checkouts_during_claude_call.append(active[0])
        return _SIMULATION_JSON

    sa_event.listen(sync_engine, "checkout", _on_checkout)
    sa_event.listen(sync_engine, "checkin", _on_checkin)
    try:
        with (
            patch.object(BaseAgent, "_call_claude", new=AsyncMock(side_effect=fake_call_claude)),
            patch(
                "cios.vector.tenant_store.TenantVectorStore.search",
                new=AsyncMock(return_value=[]),
            ),
        ):
            result = await _run_simulation_async(tenant_id, str(uuid.uuid4()), simulation_id, {})
    finally:
        sa_event.remove(sync_engine, "checkout", _on_checkout)
        sa_event.remove(sync_engine, "checkin", _on_checkin)

    assert checkouts_during_claude_call, "the mocked Claude call never ran"
    assert max(checkouts_during_claude_call) == 0, (
        "task held a pooled DB connection while waiting on Claude "
        f"(samples {checkouts_during_claude_call})"
    )
    assert result["status"] == "completed"


@pytest.mark.anyio
async def test_simulation_failure_path_writes_through_a_fresh_session():
    """A parse failure (or any exception) after the Claude call must still
    land a "failed" status + error_message — on its own fresh session, not
    the one the try block was using. Before the fix, the failure handler
    reused that same session; if it had died from being held open across
    the Claude call, this commit would raise too and silently lose the
    failure record along with the result.
    """
    from cios.tasks.simulation import _run_simulation_async

    tenant_id, simulation_id = await _create_tenant_opp_and_sim()

    async def fake_call_claude(system_prompt: str, *args, **kwargs) -> str:
        return "not valid json at all"

    with (
        patch.object(BaseAgent, "_call_claude", new=AsyncMock(side_effect=fake_call_claude)),
        patch(
            "cios.vector.tenant_store.TenantVectorStore.search",
            new=AsyncMock(return_value=[]),
        ),
        pytest.raises(ValueError, match="not valid JSON"),
    ):
        await _run_simulation_async(tenant_id, str(uuid.uuid4()), simulation_id, {})

    async with async_session_factory() as db:
        await _set_tenant(db, uuid.UUID(tenant_id))
        row = (
            await db.execute(
                select(AwardSimulation).where(AwardSimulation.id == uuid.UUID(simulation_id))
            )
        ).scalar_one()
        assert row.status == "failed"
        assert row.error_message is not None
