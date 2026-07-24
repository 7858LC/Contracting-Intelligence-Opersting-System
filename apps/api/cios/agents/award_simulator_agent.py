"""
Award Simulator Agent — Flagship CIOS Feature.

Emulates government source selection evaluation to predict award probability,
surface weaknesses/deficiencies, and generate red team commentary.

Based on FAR 15.305, FAR 15.306 (competitive range), FAR 15.308 (source selection
decision), and DoD Source Selection Procedures.
"""

from typing import Any

from cios.agents.base import AgentContext, BaseAgent
from cios.config import settings

AWARD_SIMULATOR_SYSTEM_PROMPT = """You are a Source Selection Authority (SSA) simulation engine
within CIOS. You emulate how government evaluators assess proposals under FAR Part 15.

YOUR ROLE:
You evaluate a contractor's position AS IF you were a government source selection board.
You use adjectival and color ratings where applicable.

EVALUATION FRAMEWORKS YOU IMPLEMENT:

1. FAR 15.305 TRADEOFF PROCESS:
   - Technical/Management Approach
   - Past Performance
   - Price/Cost

2. DOD COLOR/ADJECTIVAL RATINGS (DFARS PGI 215.3):
   - Blue/Outstanding (95-100): Proposal exceeds requirements, very low risk
   - Purple/Good (80-94): Proposal exceeds some requirements, low risk
   - Green/Acceptable (65-79): Proposal meets requirements, moderate risk
   - Yellow/Marginal (40-64): Proposal does not clearly meet requirements, high risk
   - Red/Unacceptable (0-39): Proposal fails to meet requirements, cannot be corrected

3. PAST PERFORMANCE RATINGS (PPIRS):
   - Exceptional (5): Performance significantly exceeds expectations
   - Very Good (4): Performance exceeds expectations
   - Satisfactory (3): Performance meets expectations
   - Marginal (2): Performance does not meet some expectations
   - Unsatisfactory (1): Performance does not meet expectations

4. RISK RATINGS:
   - Low: Little doubt performance will be successful
   - Moderate: Some doubt performance will be successful
   - High: Significant doubt performance will be successful

EVALUATION RULES:
- Weaknesses are aspects that increase risk of unsuccessful contract performance
- Significant Weaknesses are flaws that appreciably increase risk
- Deficiencies are material failures that cannot be corrected without a rewrite
- Strengths exceed requirements in ways that benefit the government

You evaluate with the impartiality and rigor of a trained government evaluator.
You cite FAR/DFARS sections for every finding.
You always provide suggested improvements — you are a red team, not just an evaluator.

OUTPUT FORMAT — respond with ONLY valid JSON, no markdown fences, no prose:
{
  "technical_score": <0-100>,
  "management_score": <0-100>,
  "past_performance_score": <0-100>,
  "price_competitiveness_score": <0-100>,
  "compliance_score": <0-100>,
  "risk_score": <0-100>,
  "overall_score": <0-100>,
  "award_probability": <0.0-1.0>,
  "confidence_score": <0.0-1.0>,
  "gate_review_recommendation": "<SUBMIT|REVISE|WITHDRAW>",
  "executive_summary": "<2-3 paragraph board-level narrative>",
  "factor_ratings": {
    "<factor_name>": {
      "score": <0-100>,
      "adjectival": "<Outstanding|Good|Acceptable|Marginal|Unacceptable>",
      "color": "<Blue|Purple|Green|Yellow|Red>",
      "risk": "<Low|Moderate|High>",
      "narrative": "<evaluator narrative paragraph>"
    }
  },
  "strengths": [{"factor": "<name>", "description": "<text>", "citation": "<FAR ref>"}],
  "weaknesses": [
    {"factor": "<name>", "description": "<text>", "citation": "<FAR ref>", "severity": "weakness"}
  ],
  "significant_weaknesses": [
    {"factor": "<name>", "description": "<text>", "citation": "<FAR ref>",
     "severity": "significant_weakness"}
  ],
  "deficiencies": [
    {"factor": "<name>", "description": "<text>", "citation": "<FAR ref>", "severity": "deficiency"}
  ],
  "red_team_comments": [{"observation": "<text>", "impact": "<text>", "recommendation": "<text>"}],
  "suggested_improvements": [
    {"title": "<short title>", "description": "<text>", "expected_score_impact": "<+N points>",
     "priority": "<high|medium|low>", "factor": "<factor_name>"}
  ],
  "rule_citations": [
    {"regulation": "<FAR|DFARS|etc>", "section": "<section>", "text": "<quoted text>"}
  ],
  "risks": [{"description": "<risk>", "likelihood": "<high|medium|low>", "mitigation": "<text>"}]
}"""


class AwardSimulatorAgent(BaseAgent):
    name = "award_simulator_agent"
    model = settings.anthropic_model_ceo
    max_tokens = 16384
    temperature = 0.0

    async def _execute(self, context: AgentContext, **kwargs: Any) -> dict[str, Any]:
        opportunity_data: dict = kwargs.get("opportunity_data", {})
        proposal_content: dict = kwargs.get("proposal_content", {})
        knowledge_context: list[dict] = kwargs.get("knowledge_context", [])
        evaluation_factors: list[dict] = kwargs.get("evaluation_factors", [])
        evaluation_methodology: str = kwargs.get("evaluation_methodology", "BEST_VALUE_TRADEOFF")
        rule_pack: str = context.rule_pack

        evidence_block = self._build_evidence_block(knowledge_context[:8])

        eval_factors_block = (
            "\n".join(
                f"- {f.get('name', 'Factor')}: Weight {f.get('weight', 1.0)}, "
                f"Type {f.get('type', 'technical')}"
                for f in evaluation_factors
            )
            or "Not specified — use standard FAR 15.305 factors"
        )

        user_message = f"""
SOURCE SELECTION SIMULATION
============================
SOLICITATION: {opportunity_data.get("title", "Unknown")}
AGENCY: {opportunity_data.get("agency", "Unknown")}
SOLICITATION NUMBER: {opportunity_data.get("solicitation_number", "Unknown")}
EVALUATION METHODOLOGY: {evaluation_methodology}
CONTRACT TYPE: {opportunity_data.get("contract_type", "Unknown")}
PROCUREMENT RULE PACK: {rule_pack}

EVALUATION FACTORS (in priority order):
{eval_factors_block}

SOLICITATION REQUIREMENTS SUMMARY:
{opportunity_data.get("description", "Not provided")[:2000]}

KEY REQUIREMENTS:
{opportunity_data.get("key_requirements", [])}

OFFEROR PROFILE (from Knowledge Vault):
{evidence_block}

PROPOSAL CONTENT PROVIDED:
Technical Volume: {proposal_content.get("technical", "Not provided")[:1000]}
Management Volume: {proposal_content.get("management", "Not provided")[:500]}
Past Performance: {proposal_content.get("past_performance", "Not provided")[:500]}
Price: {proposal_content.get("price", "Not provided")}

---

SIMULATION INSTRUCTIONS:
Perform a complete source selection evaluation AS IF you are the government SSA and SSEB.

For each evaluation factor, provide:
1. Adjectival/Color Rating
2. Risk Rating (Low/Moderate/High)
3. Numerical Score (0–100)
4. Weight applied
5. Strengths identified (with citation)
6. Weaknesses identified (with citation and FAR reference)
7. Significant Weaknesses (with citation)
8. Deficiencies (with citation) — these are disqualifying
9. Suggested improvements (red team)
10. Evaluator narrative (as a government evaluator would write it)

Then provide:
- Overall Technical Score (0–100)
- Past Performance Score (0–100) with PPIRS rating
- Price Competitiveness Score (0–100)
- Risk Score (0–100, higher = less risk)
- Compliance Score (0–100)
- Award Probability (0.0–1.0) with basis
- Gate Review Recommendation: SUBMIT / REVISE / WITHDRAW
- Executive Summary (2–3 paragraphs, board-level language)
- Top 5 Improvements with expected score impact
- Red Team Commentary (3–5 critical observations)
- Rule Citations (FAR/DFARS sections)

Respond as detailed structured JSON matching the AwardSimulation schema.
"""

        raw = await self._call_claude(AWARD_SIMULATOR_SYSTEM_PROMPT, user_message)

        return {
            "simulation": raw,
            "opportunity_title": opportunity_data.get("title"),
            "evaluation_methodology": evaluation_methodology,
            "rule_pack": rule_pack,
            "agent": self.name,
            "model": self.model,
        }
