"""
Compliance Director — procurement rule engine and compliance gap analysis.
Module 3 (Procurement Rule Engine) + Module 4 (Compliance Engine)
"""
from typing import Any

from cios.agents.base import AgentContext, BaseAgent


COMPLIANCE_SYSTEM_PROMPT = """You are the Compliance Director for CIOS, an expert in
procurement regulations across all government jurisdictions.

Your expertise covers:
- Federal: FAR, DFARS, GSAM, agency supplements (NASA FAR, HHSAR, etc.)
- State: Uniform Procurement Acts, state-specific codes
- Municipal/County: Local procurement ordinances
- International: EU Public Procurement Directives, World Bank procurement rules
- Education: Uniform Guidance (2 CFR 200), state education codes
- Healthcare: CMS procurement rules, state Medicaid requirements
- Defense: CMMC, NIST 800-171, ITAR/EAR compliance

COMPLIANCE ASSESSMENT FRAMEWORK:
1. Identify mandatory requirements (go/no-go criteria)
2. Score compliance readiness per requirement
3. Flag deficiencies with remediation timeline
4. Assess CMMC/NIST readiness for defense opportunities
5. Identify small business compliance requirements

You never make compliance determinations without citing the specific regulation section.
You distinguish between mandatory requirements and evaluation factors.

OUTPUT: Structured JSON with compliance matrix, deficiency findings, and remediation roadmap."""


class ComplianceDirector(BaseAgent):
    name = "compliance_director"

    async def _execute(self, context: AgentContext, **kwargs: Any) -> dict[str, Any]:
        opportunity_data: dict = kwargs.get("opportunity_data", {})
        knowledge_context: list[dict] = kwargs.get("knowledge_context", [])

        user_message = f"""
COMPLIANCE ASSESSMENT
=====================
Opportunity: {opportunity_data.get('title', 'Unknown')}
Agency: {opportunity_data.get('agency', 'Unknown')}
Jurisdiction: {opportunity_data.get('jurisdiction', 'federal')}
Rule Pack: {context.rule_pack}
Contract Type: {opportunity_data.get('contract_type', 'Unknown')}
Set-Aside: {opportunity_data.get('set_aside_type', 'None')}
Key Requirements: {opportunity_data.get('key_requirements', [])}

Organizational Context: {[k.get('content', '')[:200] for k in knowledge_context[:3]]}

Perform comprehensive compliance assessment:
1. Mandatory requirements matrix (go/no-go)
2. Compliance score per requirement (0–100)
3. Deficiency findings with severity (critical/major/minor)
4. Regulatory citations for each finding
5. Remediation roadmap with timelines
6. CMMC/NIST 800-171 gap analysis (if applicable)
7. Small business compliance requirements
8. Subcontracting plan requirements

Flag all showstoppers (deficiencies that would disqualify the proposal).
Respond as structured JSON.
"""
        raw = await self._call_claude(COMPLIANCE_SYSTEM_PROMPT, user_message)
        return {"compliance_assessment": raw, "agent": self.name}
