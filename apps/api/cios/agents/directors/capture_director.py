"""
Capture Director — orchestrates bid/no-bid analysis and award probability.
Manages: BidAnalystAgent, AwardProbabilityAgent, ProposalReadinessAgent
"""

from typing import Any

from cios.agents.base import AgentContext, BaseAgent

CAPTURE_SYSTEM_PROMPT = """You are the Capture Director for CIOS, an expert in federal and
public-sector capture management with deep knowledge of FAR, DFARS, and state procurement codes.

Your responsibilities:
1. Assess bid/no-bid viability with evidence-based scoring
2. Estimate award probability using historic patterns and opportunity signals
3. Evaluate proposal readiness across all evaluation factors
4. Identify capture actions required to improve win probability
5. Recommend pipeline prioritization

You assess opportunities using the Shipley capture management framework adapted for
AI-assisted analysis. You never overstate confidence. You always cite the specific
evaluation criteria from the solicitation.

Scoring methodology (0–100 scale):
- 90-100: Exceptional position / very high confidence
- 75-89: Strong position / high confidence
- 60-74: Competitive position / moderate confidence
- 45-59: Borderline / requires significant effort
- <45: Unfavorable / recommend No-Bid

OUTPUT: Structured JSON with scores, rationale, evidence, and action items."""


class CaptureDirector(BaseAgent):
    name = "capture_director"

    async def _execute(self, context: AgentContext, **kwargs: Any) -> dict[str, Any]:
        opportunity_data: dict = kwargs.get("opportunity_data", {})
        knowledge_context: list[dict] = kwargs.get("knowledge_context", [])

        evidence_block = self._build_evidence_block(knowledge_context[:5])

        user_message = f"""
CAPTURE ASSESSMENT
==================
Opportunity: {opportunity_data.get("title", "Unknown")}
Agency: {opportunity_data.get("agency", "Unknown")}
Value: ${opportunity_data.get("estimated_value_max", "Unknown")}
Solicitation Type: {opportunity_data.get("solicitation_type", "Unknown")}
Set-Aside: {opportunity_data.get("set_aside_type", "None")}
NAICS: {opportunity_data.get("naics_codes", [])}
Response Deadline: {opportunity_data.get("response_deadline", "Unknown")}
Evaluation Criteria: {opportunity_data.get("evaluation_criteria", [])}
Incumbent: {opportunity_data.get("incumbent", "Unknown")}

ORGANIZATIONAL EVIDENCE:
{evidence_block}

Perform complete capture assessment:
1. Strategic fit score (0-100) with rationale
2. Win probability estimate (0-100) with basis
3. Proposal readiness score (0-100) by factor
4. Gap analysis (capability, past performance, relationships)
5. Capture actions ranked by impact
6. Bid/No-Bid recommendation with confidence score
7. Risk factors with mitigation strategies

Cite specific FAR/DFARS sections or applicable procurement rules.
Respond as structured JSON.
"""
        raw = await self._call_claude(CAPTURE_SYSTEM_PROMPT, user_message)

        return {
            "capture_assessment": raw,
            "opportunity_title": opportunity_data.get("title"),
            "agent": self.name,
        }
