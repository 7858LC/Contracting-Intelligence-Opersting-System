"""Research Analyst Agent — synthesizes aggregated agency buying-pattern data
into the Agency Intelligence Brief narrative.

Director-tier (not Analyst/Haiku): this produces executive-facing research
content distributed to Executive Council members, not a per-company signal
scan, so it's priced and prompted like the other Director-tier agents.

Reads only from AgencyBuyingPattern (platform-owned, public-data-derived) —
never touches tenant data, consistent with cios/models/research.py's
tenant-isolation exception.
"""

from __future__ import annotations

import json
from typing import Any

from cios.config import settings

from .base import AgentContext, BaseAgent

_SYSTEM_PROMPT = """You are the Research Analyst for CIOS's Procurement Intelligence™ \
research program. You write the Agency Intelligence Brief — a quarterly, executive-facing \
narrative distributed to Executive Council members ahead of any public release.

Your input is aggregated, public-data-derived award activity for one federal agency over \
one quarter (from USASpending.gov). You have NOT seen individual contractors' private \
capture strategies, bids, or any tenant-owned data — only this agency's own aggregate \
award activity.

Your analysis must be:
- Evidence-based: every claim ties back to a specific figure in the aggregated data provided
- Candid about data limitations: this is a bounded sample of top awards by value for the \
period, not a complete Treasury-certified total — do not claim precision the data doesn't support
- Actionable for a BD executive deciding where to focus capture resources next quarter
- Written for a senior executive audience — direct, no filler

Output ONLY valid JSON matching the exact schema provided. No preamble, no explanation."""

_USER_TEMPLATE = """Write the Agency Intelligence Brief for this agency and period.

## Agency
{agency_name}

## Period
{period_label} ({period_start} to {period_end})

## Aggregated Award Activity
Total obligated (sampled top awards): ${total_obligated:,.0f}
Award count (sampled): {award_count}
Top NAICS codes by obligated amount: {top_naics}

## Required Output (JSON)
Return a JSON object with exactly these fields:
{{
  "executive_summary": "2-3 sentence summary of this agency's buying activity this period",
  "key_findings": [
    "specific, evidence-tied finding #1",
    "specific, evidence-tied finding #2",
    "specific, evidence-tied finding #3"
  ],
  "priority_sectors": [
    {{"naics": "code", "rationale": "why this sector stands out this period"}}
  ],
  "capture_implications": "1-2 sentences: what should a BD executive reading this actually do",
  "data_limitations": "1 sentence: this is a bounded top-award sample, not a complete total",
  "confidence_explanation": "1 sentence explaining confidence in this analysis"
}}"""


class ResearchAnalystAgent(BaseAgent):
    name = "research_analyst"
    model = settings.anthropic_model_director
    max_tokens = 3072
    temperature = 0.1

    async def _execute(self, context: AgentContext, **kwargs: Any) -> dict[str, Any]:
        agency_name: str = kwargs["agency_name"]
        period_label: str = kwargs["period_label"]
        period_start: str = kwargs["period_start"]
        period_end: str = kwargs["period_end"]
        aggregate: dict[str, Any] = kwargs["aggregate"]

        top_naics = aggregate.get("top_naics_breakdown", {})
        top_naics_str = (
            ", ".join(f"{code} (${amt:,.0f})" for code, amt in top_naics.items())
            if top_naics
            else "none captured in sample"
        )

        prompt = _USER_TEMPLATE.format(
            agency_name=agency_name,
            period_label=period_label,
            period_start=period_start,
            period_end=period_end,
            total_obligated=aggregate.get("total_obligated_amount", 0.0),
            award_count=aggregate.get("award_count", 0),
            top_naics=top_naics_str,
        )

        raw = await self._call_claude(system_prompt=_SYSTEM_PROMPT, user_message=prompt)
        return _parse_brief(raw)


def _parse_brief(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        data = json.loads(text[start : end + 1]) if start != -1 and end > start else {}

    return {
        "executive_summary": str(data.get("executive_summary", "Analysis unavailable.")),
        "key_findings": _ensure_list(data.get("key_findings", [])),
        "priority_sectors": _ensure_list(data.get("priority_sectors", [])),
        "capture_implications": str(data.get("capture_implications", "")),
        "data_limitations": str(data.get("data_limitations", "")),
        "confidence_explanation": str(data.get("confidence_explanation", "")),
    }


def _ensure_list(val: Any) -> list:
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        return [val]
    return []
