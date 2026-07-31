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
from collections.abc import Set as AbstractSet


def extract_claude_json(
    raw: str, context: str, require_any_of: AbstractSet[str] | None = None
) -> dict:
    """Extract a JSON object from Claude's raw text response.

    Strips ```json ... ``` / ``` ... ``` fences if present, then falls back
    to locating the first {...} block. Raises ValueError (never silently
    returns {}) if no valid JSON object can be recovered — a parse failure
    must surface as a failure to whatever's consuming this, not silently
    succeed with nothing.

    require_any_of: optional set of expected top-level keys. When given, a
    response that parses fine but contains NONE of them is treated as a
    failure (ValueError) instead of being returned — because to a caller
    doing ``result.get("some_score")`` on every field, a schema-noncompliant
    object is indistinguishable from an empty one, and the observed live
    outcome of that is a bid decision marked "analyzed" with every score,
    the recommendation, and the rationale all silently null. Before failing,
    one known drift shape is recovered: Claude nesting the real payload
    under a single wrapper key (e.g. {"risk_assessment": {...}}), which
    risk_director produced in production before its prompt was pinned.
    """
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()

    candidates = [text]
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        candidates.append(match.group(0))

    parsed: dict | None = None
    for candidate in candidates:
        # strict=True (the default) rejects literal, unescaped control
        # characters — routinely a literal newline — inside a JSON string
        # value. Long free-text fields (rationale, description, etc.) are
        # exactly where Claude produces these; strict=False accepts them
        # instead of failing to parse an otherwise well-formed object.
        for strict in (True, False):
            try:
                result = json.loads(candidate, strict=strict)
            except (json.JSONDecodeError, ValueError):
                continue
            # A top-level array / string / number parses fine but is useless
            # to callers expecting an object — keep looking, don't return it.
            if isinstance(result, dict):
                parsed = result
                break
        if parsed is not None:
            break

    if parsed is None:
        raise ValueError(
            f"{context}: Claude response was not a valid JSON object. "
            f"First 500 chars of raw response: {text[:500]!r}"
        )

    if require_any_of and not (require_any_of & parsed.keys()):
        # Known drift shape: the real payload nested one level down under a
        # wrapper key. Unwrap it rather than failing the whole run.
        for value in parsed.values():
            if isinstance(value, dict) and (require_any_of & value.keys()):
                return value
        raise ValueError(
            f"{context}: Claude returned valid JSON but with none of the expected keys "
            f"{sorted(require_any_of)} — got top-level keys {sorted(parsed.keys())[:20]}. "
            f"First 500 chars of raw response: {text[:500]!r}"
        )

    return parsed
