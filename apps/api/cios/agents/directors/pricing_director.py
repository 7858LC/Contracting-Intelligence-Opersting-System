"""Pricing Director — price-to-win analysis and cost strategy."""

from typing import Any

from cios.agents.base import AgentContext, BaseAgent

PRICING_SYSTEM_PROMPT = """You are the Pricing Director for CIOS, expert in government
contract pricing, cost estimating, and price-to-win analysis.

Your expertise:
- Cost proposal structure (DCAA compliant)
- Price-to-win (PTW) modeling
- LPTA vs. Best Value tradeoff analysis
- Market pricing research
- FAR 15.4 pricing requirements
- GSA Schedule pricing
- IDIQ ceiling and task order pricing
- SCA/DBA wage determinations
- Profit analysis (FAR 15.404-4)

ANALYTICAL APPROACH:
1. Establish price-to-win range from market data
2. Model competitors' likely pricing strategies
3. Assess evaluation methodology impact on price strategy
4. Identify cost drivers and areas for competitive pricing
5. Risk-adjusted pricing recommendations

You never provide specific price recommendations without market basis.
You always note assumptions in cost models.

OUTPUT: Structured JSON with PTW analysis, pricing strategy, and cost driver assessment."""


class PricingDirector(BaseAgent):
    name = "pricing_director"

    async def _execute(self, context: AgentContext, **kwargs: Any) -> dict[str, Any]:
        opportunity_data: dict = kwargs.get("opportunity_data", {})
        knowledge_context: list[dict] = kwargs.get("knowledge_context", [])

        user_message = f"""
PRICING INTELLIGENCE ASSESSMENT
================================
Opportunity: {opportunity_data.get("title", "Unknown")}
Agency: {opportunity_data.get("agency", "Unknown")}
Estimated Value: ${opportunity_data.get("estimated_value_max", "Unknown")}
Evaluation Methodology: {opportunity_data.get("evaluation_methodology", "Best Value TRADEOFF")}
Contract Type: {opportunity_data.get("contract_type", "Unknown")}
Period of Performance: {opportunity_data.get("period_of_performance_start", "?")} to \
{opportunity_data.get("period_of_performance_end", "?")}

Pricing Context from Knowledge Vault: {[k.get("content", "")[:150] for k in knowledge_context[:3]]}

Perform pricing intelligence assessment:
1. Price-to-win estimate range (low/mid/high)
2. Pricing strategy recommendation (aggressive/competitive/conservative)
3. Key cost drivers
4. Evaluation methodology impact on pricing strategy
5. Competitor pricing tendencies
6. Profit rate benchmark for this contract type
7. Risk adjustments required
8. FAR pricing requirement flags

Cite relevant FAR sections (e.g., FAR 15.4, 52.215-2).
Respond as structured JSON.
"""
        raw = await self._call_claude(PRICING_SYSTEM_PROMPT, user_message)
        return {"pricing_assessment": raw, "agent": self.name}
