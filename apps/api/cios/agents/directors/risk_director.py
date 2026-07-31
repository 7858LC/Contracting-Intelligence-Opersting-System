"""Risk Director — technical, programmatic, and financial risk analysis."""

from typing import Any

from cios.agents.base import AgentContext, BaseAgent

RISK_SYSTEM_PROMPT = """You are the Risk Director for CIOS, expert in government contract
risk assessment and risk-based bid decisions.

RISK TAXONOMY (aligned with FAR 15.305 and DoD risk framework):
- Technical Risk: Can we deliver the technical solution?
- Schedule Risk: Can we meet the period of performance?
- Cost Risk: Can we deliver within budget?
- Management Risk: Do we have the right team and processes?
- Past Performance Risk: Does our record support a favorable CPARS?
- Counterparty Risk: Is the customer a reliable payer?
- Regulatory/Compliance Risk: CMMC, ITAR, security clearances
- Competitive Risk: Are we outclassed by incumbents or large primes?
- Strategic Risk: Does this align with our growth strategy?
- Financial Risk: Is the cost of bidding proportionate to probability?

RISK RATING SCALE:
- High: Likely to impact contract execution significantly
- Medium: May impact execution, mitigation required
- Low: Manageable with standard practices
- Very Low: Negligible impact expected

For each risk: Probability (0–1), Impact (1–5), Score = Probability × Impact × 20
Provide mitigation strategies with responsible party recommendations.

Use the taxonomy and methodology above only as your internal analysis process. Do NOT
reproduce that process in your output. Output ONLY the following JSON object — no markdown
fences, no preamble or closing remarks, no extra top-level keys (no "metadata", no
"risk_assessment" wrapper, no "risk_register"), and no multi-paragraph fields:
{
  "risk_score": 0,
  "risks": [
    {"description": "specific risk #1, one plain sentence", "severity": "high"},
    {"description": "specific risk #2, one plain sentence", "severity": "medium"}
  ]
}
"risk_score" is a single number 0-100 (higher = riskier). Each "risks" entry is a flat object
with a one-sentence "description" and a "severity" of "low"/"medium"/"high"/"very_high" —
never grouped by taxonomy category, never more than one sentence per description."""


class RiskDirector(BaseAgent):
    name = "risk_director"
    # See capture_director.py's comment — 8192 was the value that actually
    # truncated live in production for this agent specifically; 16384
    # matches AwardSimulatorAgent's already-proven-sufficient budget.
    max_tokens = 16384

    async def _execute(self, context: AgentContext, **kwargs: Any) -> dict[str, Any]:
        opportunity_data: dict = kwargs.get("opportunity_data", {})
        knowledge_context: list[dict] = kwargs.get("knowledge_context", [])

        user_message = f"""
RISK ASSESSMENT
===============
Opportunity: {opportunity_data.get("title", "Unknown")}
Agency: {opportunity_data.get("agency", "Unknown")}
Value: ${opportunity_data.get("estimated_value_max", "Unknown")}
Contract Type: {opportunity_data.get("contract_type", "Unknown")}
Set-Aside: {opportunity_data.get("set_aside_type", "None")}
Key Requirements: {opportunity_data.get("key_requirements", [])}
Incumbent: {opportunity_data.get("incumbent", "Unknown")}
Response Deadline: {opportunity_data.get("response_deadline", "Unknown")}

Organizational Context: {[k.get("content", "")[:150] for k in knowledge_context[:3]]}

Analyze internally across all taxonomy categories, the probability × impact matrix, mitigation
strategies, residual risk, and the top showstopper risks — then condense that analysis into
the exact JSON schema specified in your system prompt. Every risk you identify becomes one
entry in the "risks" array; nothing else about your process appears in the output.
"""
        raw = await self._call_claude(RISK_SYSTEM_PROMPT, user_message, raise_on_truncation=True)
        return {"risk_assessment": raw, "agent": self.name}
