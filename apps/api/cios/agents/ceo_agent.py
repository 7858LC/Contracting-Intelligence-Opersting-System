"""
CEO Agent — Top of the hierarchical orchestration tree.

Receives executive queries, decomposes into director tasks,
synthesizes results, and produces board-level recommendations.
Never exposed directly to users — only recommendations are surfaced.
"""

from typing import Any

from cios.config import settings

from .base import AgentContext, BaseAgent

CEO_SYSTEM_PROMPT = """You are the Chief Intelligence Officer of CIOS — the Contract Intelligence
Operating System. You operate at the executive level of a hierarchical AI system designed to help
government contractors increase their award probability.

Your role:
1. Synthesize intelligence from all Director-level agents
2. Produce board-level capture strategy recommendations
3. Identify cross-cutting risks and opportunities
4. Make gate-review recommendations (Bid / No-Bid / Conditional)
5. Identify portfolio-level strategic implications

CORE PRINCIPLES:
- You NEVER make recommendations without evidence
- Every conclusion includes confidence score (0.0–1.0)
- Every recommendation cites applicable procurement regulations
- You surface assumptions explicitly
- You always provide alternatives
- You acknowledge uncertainty — never simulate false confidence

You think like a seasoned BD Director with 20+ years of federal contracting experience,
combining analytical rigor with strategic insight.

Use the principles above only as your internal analysis process. Do NOT reproduce that process
in your output. Output ONLY the following JSON object — no markdown fences, no preamble or
closing remarks, no extra top-level keys (no "metadata", no "executive_summary" wrapper), and
no multi-paragraph fields:
{
  "gate_review_recommendation": "BID",
  "award_probability": 0.0,
  "confidence_score": 0.0,
  "strategic_recommendation": "one paragraph, plain text",
  "key_decision_factors": ["factor 1", "factor 2"],
  "critical_risks": [{"risk": "specific risk, one sentence", "mitigation": "one sentence"}],
  "alternatives": ["alternative course of action, one sentence"],
  "regulation_citations": ["FAR 15.305"]
}
"gate_review_recommendation" is exactly one of "BID", "NO_BID", "CONDITIONAL_BID" — never
"BID/NO-BID", never a sentence. "award_probability" and "confidence_score" are each a single
number 0.0–1.0."""


class CEOAgent(BaseAgent):
    name = "ceo_agent"
    model = settings.anthropic_model_ceo
    # See capture_director.py's comment — 8192 truncated a comparably
    # comprehensive JSON output (arrays of decision factors/risks/
    # alternatives/citations) mid-object in that sibling agent; 16384
    # matches AwardSimulatorAgent's already-proven-sufficient budget.
    max_tokens = 16384
    temperature = 0.0

    async def _execute(self, context: AgentContext, **kwargs: Any) -> dict[str, Any]:
        director_outputs: list[dict] = kwargs.get("director_outputs", [])
        query: str = kwargs.get("query", "Provide executive capture assessment")

        evidence_block = self._build_evidence_block(
            [
                {"source": o.get("agent", "director"), "content": str(o.get("result", ""))[:500]}
                for o in director_outputs
            ]
        )

        user_message = f"""
EXECUTIVE SYNTHESIS REQUEST
============================
Query: {query}
Rule Pack: {context.rule_pack}
Tenant Context: {context.metadata.get("company_profile", "Not provided")}

DIRECTOR INTELLIGENCE REPORTS:
{evidence_block}

Analyze internally: overall strategic recommendation, key decision factors, critical risks
with mitigation options, gate review recommendation, alternative courses of action, and
applicable procurement regulation citations. Then condense that analysis into the exact JSON
schema specified in your system prompt; nothing else about your reasoning appears in the output.
"""

        raw = await self._call_claude(CEO_SYSTEM_PROMPT, user_message, raise_on_truncation=True)

        return {
            "executive_summary": raw,
            "agent": self.name,
            "model": self.model,
            "director_count": len(director_outputs),
        }

    async def orchestrate_full_assessment(
        self,
        context: AgentContext,
        opportunity_data: dict[str, Any],
        knowledge_context: list[dict],
    ) -> dict[str, Any]:
        """
        Full capture assessment pipeline:
        CEO → Directors → Analysts → Synthesis
        """
        from .directors.capture_director import CaptureDirector
        from .directors.competitive_intel_director import CompetitiveIntelDirector
        from .directors.compliance_director import ComplianceDirector
        from .directors.pricing_director import PricingDirector
        from .directors.risk_director import RiskDirector

        directors = [
            CaptureDirector(),
            ComplianceDirector(),
            CompetitiveIntelDirector(),
            PricingDirector(),
            RiskDirector(),
        ]

        # Each director is independent (same opportunity_data/knowledge_context
        # in, own Claude call out — no director reads another's output), and
        # each BaseAgent owns its own AsyncAnthropic client, so there's no
        # shared state to race. Running them with asyncio.gather instead of
        # a sequential loop turns 5 sequential Claude calls (bid_analysis.py's
        # sibling 2-director task observed 130-180s per call in production —
        # 5 sequential here would run 650-900s, on top of the CEO call after,
        # against a 600s soft_time_limit) into one wall-clock cost of
        # whichever director is slowest, which is what a "results in ~60
        # seconds" UI promise actually needs to be true.
        import asyncio

        async def _run_director(director: Any) -> dict[str, Any]:
            try:
                return await director.run(
                    context,
                    opportunity_data=opportunity_data,
                    knowledge_context=knowledge_context,
                )
            except Exception as e:
                return {"agent": director.name, "error": str(e), "result": {}}

        director_outputs = list(await asyncio.gather(*(_run_director(d) for d in directors)))

        synthesis = await self.run(
            context,
            director_outputs=director_outputs,
            query=f"Full capture assessment for: {opportunity_data.get('title', 'Opportunity')}",
        )

        return {
            "synthesis": synthesis,
            "director_outputs": director_outputs,
            "orchestration": "ceo_agent",
        }
