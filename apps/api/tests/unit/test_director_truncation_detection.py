"""Found live: a real bid analysis retried forever on "not valid JSON" —
the Capture Director's response was genuinely truncated mid-JSON-object by
hitting max_tokens (4096, BaseAgent's default), which no amount of
fence-stripping or bracket-extraction can recover, since there's no closing
brace to find. CaptureDirector/RiskDirector (and the other 3 Directors, for
consistency) now request 8192 tokens and pass raise_on_truncation=True, so
a truncated response fails fast with a specific, actionable error instead
of surfacing as a generic downstream JSON parse failure.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from cios.agents.base import AgentContext
from cios.agents.directors.capture_director import CaptureDirector


@pytest.mark.anyio
async def test_capture_director_raises_clearly_on_truncated_response():
    director = CaptureDirector()

    class _TruncatedResponse:
        content = [type("C", (), {"text": '{"strategic_fit_score": 80, "win_probabil'})()]
        stop_reason = "max_tokens"

    director._client.messages.create = AsyncMock(return_value=_TruncatedResponse())

    context = AgentContext(tenant_id=uuid.uuid4(), user_id=uuid.uuid4())

    with pytest.raises(RuntimeError, match="truncated"):
        await director.run(
            context, opportunity_data={"title": "Test Opportunity"}, knowledge_context=[]
        )


def test_all_directors_request_a_realistic_token_budget():
    """BaseAgent's default (4096) was too small for what every Director is
    prompted to produce — this is the regression guard against silently
    reverting to it."""
    from cios.agents.directors.capture_director import CaptureDirector
    from cios.agents.directors.competitive_intel_director import CompetitiveIntelDirector
    from cios.agents.directors.compliance_director import ComplianceDirector
    from cios.agents.directors.pricing_director import PricingDirector
    from cios.agents.directors.risk_director import RiskDirector

    for director_cls in (
        CaptureDirector,
        RiskDirector,
        PricingDirector,
        CompetitiveIntelDirector,
        ComplianceDirector,
    ):
        assert director_cls.max_tokens >= 8192, director_cls.__name__
