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
