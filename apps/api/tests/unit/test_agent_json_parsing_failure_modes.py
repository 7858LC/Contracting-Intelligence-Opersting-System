"""V&V Campaign 6 (Business Failure Modes) — proves malformed/truncated
Claude output fails loudly instead of silently publishing a fake result.

Both agents already had a correct caller-side failure path
(pir.py's _async_analyze_company sets status="failed"+error_message;
research.py's per-agency loop appends to an errors list) that never fired
because the parse functions swallowed total parse failure into an empty
dict, which every field then read with .get(...) and generic placeholder
defaults — the exact same shape of bug fixed once already in
tasks/simulation.py's _parse_claude_json, just never applied here.
"""

from __future__ import annotations

import pytest

from cios.agents.pir_analyst_agent import _parse_analysis
from cios.agents.research_analyst_agent import _parse_brief


def test_pir_parse_analysis_raises_on_unparseable_output():
    with pytest.raises(ValueError, match="not valid JSON"):
        _parse_analysis("Sorry, I can't complete this request right now.", overall_score=50.0)


def test_pir_parse_analysis_succeeds_on_valid_json():
    raw = """{
        "executive_summary": "Test summary",
        "pain_points": ["a", "b"],
        "recommended_outreach": "Call them",
        "buying_probability": 0.7,
        "suggested_messaging": ["x"],
        "potential_stakeholders": [{"title": "VP BD", "reason": "test"}],
        "confidence_explanation": "high confidence"
    }"""
    result = _parse_analysis(raw, overall_score=50.0)
    assert result["executive_summary"] == "Test summary"
    assert result["buying_probability"] == 0.7


def test_research_parse_brief_raises_on_unparseable_output():
    with pytest.raises(ValueError, match="not valid JSON"):
        _parse_brief("I'm unable to generate this analysis.")


def test_research_parse_brief_raises_on_truncated_json():
    # A response cut off mid-object at max_tokens — no closing brace at all.
    with pytest.raises(ValueError, match="not valid JSON"):
        _parse_brief('{"executive_summary": "This looks fine but then just stops in the mid')


def test_research_parse_brief_succeeds_on_valid_json():
    raw = """```json
    {
        "executive_summary": "Agency spending is up.",
        "key_findings": ["finding 1"],
        "priority_sectors": ["IT"],
        "capture_implications": "Bid soon.",
        "data_limitations": "Sample only.",
        "confidence_explanation": "moderate"
    }
    ```"""
    result = _parse_brief(raw)
    assert result["executive_summary"] == "Agency spending is up."
