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


def test_raises_on_unparseable_output():
    with pytest.raises(ValueError, match="not valid JSON"):
        extract_claude_json("I'm unable to complete this assessment.", context="test")


def test_raises_on_empty_string():
    with pytest.raises(ValueError, match="not valid JSON"):
        extract_claude_json("", context="test")
