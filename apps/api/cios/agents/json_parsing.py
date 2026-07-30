"""Shared JSON extraction for Claude responses.

Every agent that asks Claude for structured JSON hits the same two failure
modes: the response gets wrapped in a ```json ... ``` fence despite explicit
"no markdown" instructions (routine, not exotic — Claude does this often),
and occasionally the JSON is truncated or genuinely malformed. This was
independently reimplemented at least four times in this codebase
(tasks/simulation.py, agents/research_analyst_agent.py,
agents/pir_analyst_agent.py, tasks/bid_analysis.py) with different levels of
defensiveness — bid_analysis.py's copy never stripped fences at all and
silently swallowed any failure into an empty dict, so a routine, expected
Claude response shape (fenced JSON) reliably produced an "analyzed" bid
decision with every score and the recommendation silently blank. New
callers should use this instead of writing a fifth copy.
"""

from __future__ import annotations

import json
import re


def extract_claude_json(raw: str, context: str) -> dict:
    """Extract a JSON object from Claude's raw text response.

    Strips ```json ... ``` / ``` ... ``` fences if present, then falls back
    to locating the first {...} block. Raises ValueError (never silently
    returns {}) if no valid JSON object can be recovered — a parse failure
    must surface as a failure to whatever's consuming this, not silently
    succeed with nothing.
    """
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()

    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except (json.JSONDecodeError, ValueError):
            pass

    raise ValueError(
        f"{context}: Claude response was not valid JSON. "
        f"First 500 chars of raw response: {text[:500]!r}"
    )
