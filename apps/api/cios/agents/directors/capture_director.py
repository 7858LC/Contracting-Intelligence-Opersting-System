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

Use the framework and methodology above only as your internal analysis process. Do NOT
reproduce that process, gap analysis, capture actions, or risk factors in your output — those
inform your scores and rationale but do not get their own fields. Output ONLY the following
JSON object — no markdown fences, no preamble or closing remarks, no extra top-level keys,
no multi-paragraph fields:
{
  "strategic_fit_score": 0,
  "win_probability_score": 0,
  "past_performance_score": 0,
  "capability_match_score": 0,
  "bid_no_bid_recommendation": "BID",
  "recommendation_rationale": "2-4 sentence rationale, mentioning the key gaps/actions/risks",
  "confidence_score": 0.0
}
"bid_no_bid_recommendation" must be exactly one of the plain strings "BID", "NO_BID", or
"CONDITIONAL_BID" — never an object, never a longer phrase, never anything else."""


class CaptureDirector(BaseAgent):
    name = "capture_director"
    # BaseAgent's default (4096) routinely truncated this prompt's 7-point
    # comprehensive JSON output mid-object — found live via a bid analysis
    # stuck retrying forever on "not valid JSON" (a truncated response has no
    # closing brace, so no amount of fence-stripping can recover it). Bumping
    # to 8192 wasn't enough either — the sibling RiskDirector still truncated
    # at that ceiling in production. 16384 matches AwardSimulatorAgent's
    # already-proven-sufficient budget for comparably comprehensive output.
    max_tokens = 16384

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

Analyze internally: strategic fit, win probability, proposal readiness by factor, gap
analysis (capability, past performance, relationships), capture actions ranked by impact, and
risk factors with mitigations. Cite specific FAR/DFARS sections or applicable procurement
rules in your reasoning. Then condense that analysis into the exact JSON schema specified in
your system prompt — the gaps, actions, and risks you found inform "recommendation_rationale"
but do not get their own fields.
"""
        raw = await self._call_claude(CAPTURE_SYSTEM_PROMPT, user_message, raise_on_truncation=True)

        return {
            "capture_assessment": raw,
            "opportunity_title": opportunity_data.get("title"),
            "agent": self.name,
        }
