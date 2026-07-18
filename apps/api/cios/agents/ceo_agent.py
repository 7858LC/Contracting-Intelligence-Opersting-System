"""
CEO Agent — Top of the hierarchical orchestration tree.

Receives executive queries, decomposes into director tasks,
synthesizes results, and produces board-level recommendations.
Never exposed directly to users — only recommendations are surfaced.
"""
from typing import Any

from cios.config import settings
from .base import AgentContext, BaseAgent, Recommendation


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

OUTPUT FORMAT: Always respond in structured JSON matching the Recommendation schema."""


class CEOAgent(BaseAgent):
    name = "ceo_agent"
    model = settings.anthropic_model_ceo
    max_tokens = 8192
    temperature = 0.0

    async def _execute(self, context: AgentContext, **kwargs: Any) -> dict[str, Any]:
        director_outputs: list[dict] = kwargs.get("director_outputs", [])
        query: str = kwargs.get("query", "Provide executive capture assessment")

        evidence_block = self._build_evidence_block(
            [{"source": o.get("agent", "director"), "content": str(o.get("result", ""))[:500]}
             for o in director_outputs]
        )

        user_message = f"""
EXECUTIVE SYNTHESIS REQUEST
============================
Query: {query}
Rule Pack: {context.rule_pack}
Tenant Context: {context.metadata.get('company_profile', 'Not provided')}

DIRECTOR INTELLIGENCE REPORTS:
{evidence_block}

Produce an executive-level synthesis with:
1. Overall strategic recommendation
2. Confidence score (0.0–1.0)
3. Key decision factors (top 5)
4. Critical risks (with mitigation options)
5. Gate review recommendation: BID / NO-BID / CONDITIONAL-BID
6. Alternative courses of action
7. Procurement regulation citations

Respond as structured JSON.
"""

        raw = await self._call_claude(CEO_SYSTEM_PROMPT, user_message)

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
        from .directors.compliance_director import ComplianceDirector
        from .directors.competitive_intel_director import CompetitiveIntelDirector
        from .directors.pricing_director import PricingDirector
        from .directors.risk_director import RiskDirector

        directors = [
            CaptureDirector(),
            ComplianceDirector(),
            CompetitiveIntelDirector(),
            PricingDirector(),
            RiskDirector(),
        ]

        director_outputs = []
        for director in directors:
            try:
                result = await director.run(
                    context,
                    opportunity_data=opportunity_data,
                    knowledge_context=knowledge_context,
                )
                director_outputs.append(result)
            except Exception as e:
                director_outputs.append({"agent": director.name, "error": str(e), "result": {}})

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
