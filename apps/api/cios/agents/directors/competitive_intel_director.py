"""
Competitive Intelligence Director — Module 8.
Analyzes competitive landscape, incumbency, pricing trends, and win patterns.
"""
from typing import Any

from cios.agents.base import AgentContext, BaseAgent


COMPETITIVE_INTEL_SYSTEM_PROMPT = """You are the Competitive Intelligence Director for CIOS.
You analyze competitive landscapes for government contract opportunities.

Your analysis covers:
1. Competitor identification and profiling
2. Incumbent analysis and re-compete strategy
3. Win/loss pattern analysis from public award data
4. Pricing strategy intelligence
5. Agency relationship mapping
6. Competitive positioning assessment
7. Counter-strategy development

DATA SOURCES you reason from:
- USASpending.gov award data
- SAM.gov registrations
- FPDS-NG contract data
- SEC filings for public competitors
- Press releases and capabilities statements
- Past solicitation questions and answers

ANALYTICAL FRAMEWORK:
- Porter's Five Forces adapted for government contracting
- Win/loss analysis patterns
- Competitor capability mapping
- Price-to-win modeling

You always distinguish between confirmed intelligence and inference.
You cite data sources and note confidence levels.

OUTPUT: Structured JSON with competitor profiles, positioning matrix, and counter-strategies."""


class CompetitiveIntelDirector(BaseAgent):
    name = "competitive_intel_director"

    async def _execute(self, context: AgentContext, **kwargs: Any) -> dict[str, Any]:
        opportunity_data: dict = kwargs.get("opportunity_data", {})
        knowledge_context: list[dict] = kwargs.get("knowledge_context", [])

        user_message = f"""
COMPETITIVE INTELLIGENCE ASSESSMENT
=====================================
Opportunity: {opportunity_data.get('title', 'Unknown')}
Agency: {opportunity_data.get('agency', 'Unknown')}
Value: ${opportunity_data.get('estimated_value_max', 'Unknown')}
NAICS: {opportunity_data.get('naics_codes', [])}
Incumbent: {opportunity_data.get('incumbent', 'Unknown')}
Anticipated Competitors: {opportunity_data.get('anticipated_competitors', [])}
Set-Aside: {opportunity_data.get('set_aside_type', 'None')}

Known Competitors from Knowledge Vault: {[k.get('content', '')[:150] for k in knowledge_context[:4]]}

Perform competitive intelligence assessment:
1. Competitive intensity rating (low/medium/high/very-high)
2. Incumbent analysis: strength, vulnerability, re-compete strategy
3. Top 3–5 anticipated competitors with profiles:
   - Strengths vs. our position
   - Weaknesses to exploit
   - Likely pricing approach
   - Win probability if they bid
4. Our competitive differentiators
5. Counter-strategy recommendations
6. Price-to-win estimate range
7. Win conditions (what we must do to win)

Note confidence levels for each intelligence item.
Respond as structured JSON.
"""
        raw = await self._call_claude(COMPETITIVE_INTEL_SYSTEM_PROMPT, user_message)
        return {"competitive_assessment": raw, "agent": self.name}
