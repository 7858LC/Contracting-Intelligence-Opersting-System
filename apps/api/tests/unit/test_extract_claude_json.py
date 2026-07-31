"""Found live: the PDQ (Bid/No-Bid Engine) module showed "Analyzed" with
every score and the recommendation blank. Root cause: tasks/bid_analysis.py
called a bare json.loads() on Claude's raw response with no markdown-fence
stripping at all — unlike every other JSON-parsing agent in the codebase —
so the routine, expected case (Claude wraps its JSON in a ```json fence
despite "no markdown" instructions) failed every time, silently, into an
empty dict. This is the shared extraction helper that replaced it.
"""

from __future__ import annotations

import pytest

from cios.agents.json_parsing import extract_claude_json


def test_extracts_plain_json():
    result = extract_claude_json('{"strategic_fit_score": 80}', context="test")
    assert result == {"strategic_fit_score": 80}


def test_strips_json_fenced_response():
    """This exact shape — a fenced response despite instructions not to use
    markdown — is what silently broke every bid decision analysis."""
    raw = '```json\n{"strategic_fit_score": 80, "bid_no_bid_recommendation": "BID"}\n```'
    result = extract_claude_json(raw, context="test")
    assert result == {"strategic_fit_score": 80, "bid_no_bid_recommendation": "BID"}


def test_strips_unlabeled_fenced_response():
    raw = '```\n{"risk_score": 40}\n```'
    result = extract_claude_json(raw, context="test")
    assert result == {"risk_score": 40}


def test_extracts_json_with_preamble_text():
    raw = 'Here is my assessment:\n\n{"strategic_fit_score": 65}\n\nLet me know if you need more.'
    result = extract_claude_json(raw, context="test")
    assert result == {"strategic_fit_score": 65}


def test_extracts_json_with_literal_newline_in_string_value():
    """Reproduces the live failure: risk_director's response was rejected
    with "not valid JSON" even though it was a complete, well-formed object
    — because a long free-text field contained a literal newline character
    instead of an escaped \\n, which json.loads rejects by default."""
    raw = (
        '{"risk_score": 40, "risks": '
        '[{"description": "Line one.\nLine two.", "severity": "medium"}]}'
    )
    result = extract_claude_json(raw, context="test")
    assert result["risk_score"] == 40
    assert result["risks"][0]["description"] == "Line one.\nLine two."


def test_raises_on_unparseable_output():
    with pytest.raises(ValueError, match="not a valid JSON object"):
        extract_claude_json("I'm unable to complete this assessment.", context="test")


def test_raises_on_empty_string():
    with pytest.raises(ValueError, match="not a valid JSON object"):
        extract_claude_json("", context="test")


def test_raises_on_valid_json_with_none_of_the_expected_keys():
    """The last silent path to an all-null "analyzed" bid decision: Claude
    returns something JSON-valid but shaped nothing like the schema. Parsing
    succeeds, every .get() downstream returns None, and without this guard
    the row commits as analyzed with every field blank."""
    with pytest.raises(ValueError, match="none of the expected keys"):
        extract_claude_json(
            '{"assessment_summary": "Strong opportunity", "notes": []}',
            context="test",
            require_any_of=frozenset({"strategic_fit_score", "win_probability_score"}),
        )


def test_raises_on_bare_empty_object_when_keys_required():
    with pytest.raises(ValueError, match="none of the expected keys"):
        extract_claude_json("{}", context="test", require_any_of=frozenset({"risk_score", "risks"}))


def test_unwraps_payload_nested_under_wrapper_key():
    """Observed live drift shape (risk_director, pre-prompt-pin): the real
    payload nested one level down under a single wrapper key."""
    raw = (
        '{"risk_assessment": {"risk_score": 55, '
        '"risks": [{"description": "x", "severity": "low"}]}}'
    )
    result = extract_claude_json(
        raw, context="test", require_any_of=frozenset({"risk_score", "risks"})
    )
    assert result["risk_score"] == 55
    assert result["risks"][0]["severity"] == "low"


def test_expected_keys_present_returns_object_unchanged():
    raw = '{"risk_score": 40, "risks": []}'
    result = extract_claude_json(
        raw, context="test", require_any_of=frozenset({"risk_score", "risks"})
    )
    assert result == {"risk_score": 40, "risks": []}


def test_raises_on_non_object_json():
    """A bare JSON scalar parses as valid JSON but is useless to callers
    expecting an object — must fail, not be returned as if it were a dict."""
    with pytest.raises(ValueError, match="not a valid JSON object"):
        extract_claude_json('"BID"', context="test")


def test_recovers_object_from_single_element_array():
    """A top-level one-element array is not returned as-is (callers need a
    dict) — the inner object is recovered via the {...} fallback instead."""
    result = extract_claude_json('[{"risk_score": 40, "risks": []}]', context="test")
    assert result == {"risk_score": 40, "risks": []}
