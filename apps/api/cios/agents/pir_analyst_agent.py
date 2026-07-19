"""PIR Analyst Agent — Claude-powered company intelligence analysis."""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from cios.config import settings
from cios.models.pir import PIRAIAnalysis, PIRCompany, PIRSignal
from .base import AgentContext, BaseAgent

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """You are the PIR Analyst, an expert in B2G (business-to-government) \
intelligence and procurement market analysis. Your role is to analyze companies that \
are pursuing or expanding their government contracting footprint.

Given a company profile and detected market signals, you produce a structured intelligence \
brief that helps GovCon business development professionals prioritize outreach and tailor \
their approach.

Your analysis must be:
- Evidence-based: every assertion tied to a specific signal or data point
- Actionable: specific, not generic advice
- Candid: identify real barriers and risks, not just positives
- Brief: executives read this in 90 seconds

Output ONLY valid JSON matching the exact schema provided. No preamble, no explanation."""

_USER_TEMPLATE = """Analyze this company for GovCon intelligence.

## Company Profile
Name: {name}
Domain: {domain}
SAM.gov UEI: {uei}
CAGE Code: {cage}
Industry: {industry}
Employee Count: {employee_count}
Revenue Range: {revenue_range}
Location: {city}, {state}
NAICS Codes: {naics}
Set-Aside Certifications: {set_asides}

## Signal Score Summary
Overall Signal Score: {overall_score}/100
Confidence Score: {confidence}/100
Growth Momentum: {momentum}/100
Government Readiness: {readiness}/100
Priority Tier: {tier}

## Detected Signals ({signal_count} total)
{signals_block}

## Required Output (JSON)
Return a JSON object with exactly these fields:
{{
  "executive_summary": "2-3 sentence summary of this company's GovCon posture and opportunity",
  "pain_points": [
    "specific challenge or gap #1 based on signals",
    "specific challenge or gap #2",
    "specific challenge or gap #3"
  ],
  "recommended_outreach": "1-2 sentence specific outreach strategy — who to contact, what angle",
  "buying_probability": 0.0,
  "suggested_messaging": [
    "Messaging angle 1 — tie to a specific signal",
    "Messaging angle 2",
    "Messaging angle 3"
  ],
  "potential_stakeholders": [
    {{"title": "Capture Manager", "reason": "Actively hiring suggests BD build-out"}},
    {{"title": "VP Business Development", "reason": "Decision maker for BD tooling"}}
  ],
  "confidence_explanation": "1 sentence explaining confidence in this analysis"
}}

buying_probability: float 0.0–1.0 reflecting likelihood of near-term procurement engagement.
- 0.8–1.0: actively building GovCon capability (multiple hiring + recent awards)
- 0.5–0.8: expanding presence (moderate signals, some awards)
- 0.2–0.5: early stage or sporadic activity
- 0.0–0.2: limited signals, not a near-term prospect"""


def _format_signals_block(signals: list[PIRSignal], max_signals: int = 20) -> str:
    if not signals:
        return "No signals detected."
    lines = []
    for sig in sorted(signals, key=lambda s: s.detected_at, reverse=True)[:max_signals]:
        age_days = (datetime.now(UTC) - sig.detected_at).days
        lines.append(
            f"- [{sig.signal_type}] {sig.title} "
            f"(source: {sig.source}, {age_days}d ago, weight: {sig.effective_weight:.1f})"
        )
    return "\n".join(lines)


class PIRAnalystAgent(BaseAgent):
    """Analyst-tier agent: uses claude-haiku for speed and volume."""

    name = "pir_analyst"
    max_tokens = 2048
    temperature = 0.1

    @property
    def model(self) -> str:  # type: ignore[override]
        return settings.anthropic_model_analyst

    async def _execute(self, context: AgentContext, **kwargs: Any) -> dict[str, Any]:
        company: PIRCompany = kwargs["company"]
        signals: list[PIRSignal] = kwargs.get("signals", [])

        prompt = _USER_TEMPLATE.format(
            name=company.name,
            domain=company.domain or "unknown",
            uei=company.samgov_uei or "not registered",
            cage=company.cage_code or "n/a",
            industry=company.industry or "unknown",
            employee_count=company.employee_count_range or "unknown",
            revenue_range=company.revenue_range or "unknown",
            city=company.headquarters_city or "unknown",
            state=company.headquarters_state or "unknown",
            naics=", ".join(company.naics_codes[:5]) if company.naics_codes else "none",
            set_asides=", ".join(company.set_aside_types) if company.set_aside_types else "none",
            overall_score=round(company.overall_signal_score, 1),
            confidence=round(company.confidence_score, 1),
            momentum=round(company.growth_momentum_score, 1),
            readiness=round(company.government_readiness_score, 1),
            tier=company.priority_tier,
            signal_count=len(signals),
            signals_block=_format_signals_block(signals),
        )

        raw = await self._call_claude(
            system_prompt=_SYSTEM_PROMPT,
            user_message=prompt,
            model=self.model,
        )

        return _parse_analysis(raw, company.overall_signal_score)


def _parse_analysis(raw: str, overall_score: float) -> dict[str, Any]:
    """Parse Claude's JSON output with graceful degradation."""
    # Strip markdown fences if present
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Best-effort: extract from partial JSON
        data = _extract_partial_json(text)

    return {
        "executive_summary": str(data.get("executive_summary", "Analysis unavailable.")),
        "pain_points": _ensure_list(data.get("pain_points", [])),
        "recommended_outreach": str(data.get("recommended_outreach", "")),
        "buying_probability": _clamp_float(data.get("buying_probability", overall_score / 100.0)),
        "suggested_messaging": _ensure_list(data.get("suggested_messaging", [])),
        "potential_stakeholders": _ensure_list(data.get("potential_stakeholders", [])),
        "confidence_explanation": str(data.get("confidence_explanation", "")),
    }


def _ensure_list(val: Any) -> list:
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        return [val]
    return []


def _clamp_float(val: Any) -> float:
    try:
        return max(0.0, min(1.0, float(val)))
    except (TypeError, ValueError):
        return 0.0


def _extract_partial_json(text: str) -> dict:
    """Last-resort: find the first {...} block in the text."""
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return {}


async def run_pir_analysis(
    company: PIRCompany,
    signals: list[PIRSignal],
    tenant_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Convenience wrapper: run analysis and return parsed result dict."""
    agent = PIRAnalystAgent()
    ctx = AgentContext(
        tenant_id=tenant_id,
        user_id=user_id or uuid.uuid4(),
    )
    run = await agent.run(ctx, company=company, signals=signals)
    return run["result"]
