"""Rule pack registry — maps jurisdiction identifiers to rule definitions."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvaluationFactor:
    name: str
    weight: float
    factor_type: str
    description: str
    rating_scale: str = "adjectival"
    is_mandatory: bool = False


@dataclass
class RulePack:
    id: str
    name: str
    jurisdiction: str
    authority: str
    primary_regulation: str
    version: str
    evaluation_factors: list[EvaluationFactor] = field(default_factory=list)
    mandatory_requirements: list[str] = field(default_factory=list)
    evaluation_methodologies: list[str] = field(default_factory=list)
    thresholds: dict[str, Any] = field(default_factory=dict)
    notes: str = ""


US_FEDERAL_FAR = RulePack(
    id="us_federal_far",
    name="US Federal — Federal Acquisition Regulation",
    jurisdiction="federal",
    authority="GSA / DoD / NASA",
    primary_regulation="48 CFR Parts 1–53",
    version="2024-01",
    evaluation_methodologies=["LPTA", "BEST_VALUE_TRADEOFF", "SOLE_SOURCE"],
    mandatory_requirements=[
        "SAM.gov registration active",
        "NAICS code match",
        "Set-aside eligibility verified",
        "Integrity and ethics certifications",
        "Buy American Act compliance",
    ],
    evaluation_factors=[
        EvaluationFactor("Technical Approach", 0.40, "technical", "FAR 15.305(a)", "DOD_COLOR"),
        EvaluationFactor("Management Approach", 0.20, "management", "FAR 15.305(a)", "DOD_COLOR"),
        EvaluationFactor("Past Performance", 0.20, "past_performance", "FAR 15.305(a)(2)", "PPIRS"),
        EvaluationFactor("Price/Cost", 0.20, "price", "FAR 15.305(a)(1)", "numeric"),
    ],
    thresholds={
        "micro_purchase": 10_000,
        "simplified_acquisition": 250_000,
        "sole_source_competitive": 750_000,
        "full_and_open_competition": 250_000,
    },
)

US_FEDERAL_DFARS = RulePack(
    id="us_federal_dfars",
    name="US Federal — Defense FAR Supplement",
    jurisdiction="federal_defense",
    authority="DoD",
    primary_regulation="48 CFR Chapter 2",
    version="2024-01",
    evaluation_methodologies=["LPTA", "BEST_VALUE_TRADEOFF", "BEST_VALUE_CONTINUUM"],
    mandatory_requirements=[
        "CMMC level certification (if applicable)",
        "Security clearance (if applicable)",
        "ITAR/EAR compliance",
        "NIST 800-171 compliance",
        "SAM.gov registration",
    ],
    evaluation_factors=[
        EvaluationFactor("Technical/Management Approach", 0.40, "technical", "DFARS 215.3", "DOD_COLOR"),
        EvaluationFactor("Past Performance", 0.30, "past_performance", "DFARS 215.305", "PPIRS"),
        EvaluationFactor("Price", 0.20, "price", "DFARS 215.4", "numeric"),
        EvaluationFactor("Small Business Utilization", 0.10, "small_business", "DFARS 252.219", "DOD_COLOR"),
    ],
    thresholds={
        "commercial_item": 2_000_000,
        "certified_cost_data": 2_000_000,
        "source_selection_board": 10_000_000,
    },
)

STATE_GENERIC = RulePack(
    id="state_generic",
    name="State Government — Generic Uniform Procurement",
    jurisdiction="state",
    authority="State Procurement Authority",
    primary_regulation="Uniform Commercial Code / State Procurement Act",
    version="2024-01",
    evaluation_methodologies=["LPTA", "BEST_VALUE", "COMPETITIVE_SEALED_BIDS"],
    mandatory_requirements=[
        "State business registration",
        "Vendor registration in state system",
        "Insurance certificates",
        "Performance bond (construction)",
    ],
    evaluation_factors=[
        EvaluationFactor("Technical Capability", 0.35, "technical", "State procurement code", "numeric"),
        EvaluationFactor("Cost/Price", 0.35, "price", "State procurement code", "numeric"),
        EvaluationFactor("Experience/Past Performance", 0.20, "past_performance", "State code", "numeric"),
        EvaluationFactor("Small/Disadvantaged Business", 0.10, "small_business", "State SBE law", "numeric"),
    ],
    thresholds={
        "informal_quotes": 25_000,
        "formal_rfp": 100_000,
    },
)

EU_PUBLIC_PROCUREMENT = RulePack(
    id="eu_public_procurement",
    name="European Union — Public Procurement Directives",
    jurisdiction="eu",
    authority="European Commission",
    primary_regulation="Directive 2014/24/EU",
    version="2024-01",
    evaluation_methodologies=["MEAT", "LOWEST_PRICE", "OPEN_PROCEDURE", "RESTRICTED_PROCEDURE"],
    mandatory_requirements=[
        "EU business registration",
        "ESPD (European Single Procurement Document)",
        "Tax compliance certificate",
        "Social security compliance",
    ],
    evaluation_factors=[
        EvaluationFactor("Quality/Technical Merit", 0.40, "technical", "Art. 67, Dir. 2014/24/EU", "numeric"),
        EvaluationFactor("Price", 0.30, "price", "Art. 67, Dir. 2014/24/EU", "numeric"),
        EvaluationFactor("Environmental/Social Criteria", 0.20, "sustainability", "Art. 67", "numeric"),
        EvaluationFactor("After-Sales Service", 0.10, "service", "Art. 67", "numeric"),
    ],
    thresholds={
        "below_threshold": 140_000,
        "above_threshold_services": 140_000,
        "above_threshold_works": 5_382_000,
    },
)

WORLD_BANK = RulePack(
    id="world_bank",
    name="World Bank — Procurement Regulations",
    jurisdiction="multilateral",
    authority="World Bank Group",
    primary_regulation="Procurement Regulations for IPF Borrowers (2016, rev. 2020)",
    version="2020-07",
    evaluation_methodologies=["QCBS", "QBS", "LCS", "FBS", "CQS", "DC"],
    mandatory_requirements=[
        "World Bank vendor registration",
        "Country eligibility confirmation",
        "Debarment check",
        "Anti-corruption declaration",
    ],
    evaluation_factors=[
        EvaluationFactor("Technical Proposal", 0.70, "technical", "Sec. IV, WB Proc. Regs.", "numeric_100"),
        EvaluationFactor("Financial Proposal", 0.30, "price", "Sec. IV, WB Proc. Regs.", "numeric_100"),
    ],
    thresholds={
        "shopping": 100_000,
        "ncb": 1_000_000,
        "icb": 1_000_000,
    },
)


class RulePackRegistry:
    _packs: dict[str, RulePack] = {
        "us_federal_far": US_FEDERAL_FAR,
        "us_federal_dfars": US_FEDERAL_DFARS,
        "state_generic": STATE_GENERIC,
        "eu_public_procurement": EU_PUBLIC_PROCUREMENT,
        "world_bank": WORLD_BANK,
    }

    def get(self, pack_id: str) -> RulePack | None:
        return self._packs.get(pack_id)

    def list_packs(self) -> list[dict]:
        return [
            {"id": p.id, "name": p.name, "jurisdiction": p.jurisdiction, "authority": p.authority}
            for p in self._packs.values()
        ]

    def get_evaluation_factors(self, pack_id: str) -> list[dict]:
        pack = self.get(pack_id)
        if not pack:
            return []
        return [
            {
                "name": f.name,
                "weight": f.weight,
                "type": f.factor_type,
                "description": f.description,
                "rating_scale": f.rating_scale,
                "is_mandatory": f.is_mandatory,
            }
            for f in pack.evaluation_factors
        ]
