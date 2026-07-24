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

OUTPUT: Structured JSON with risk register, risk matrix, and go/no-go risk threshold."""


class RiskDirector(BaseAgent):
    name = "risk_director"

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

Produce comprehensive risk register:
1. Risk identification across all taxonomy categories
2. Risk rating (probability × impact matrix)
3. Risk score (0–100)
4. Mitigation strategies for each High/Medium risk
5. Residual risk after mitigation
6. Bid/No-Bid risk threshold assessment
7. Top 3 showstopper risks

Rate overall risk level: LOW / MEDIUM / HIGH / VERY HIGH
Include risk-adjusted win probability modifier.
Respond as structured JSON.
"""
        raw = await self._call_claude(RISK_SYSTEM_PROMPT, user_message)
        return {"risk_assessment": raw, "agent": self.name}
