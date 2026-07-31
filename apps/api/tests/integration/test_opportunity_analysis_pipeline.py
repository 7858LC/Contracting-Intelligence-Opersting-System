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
