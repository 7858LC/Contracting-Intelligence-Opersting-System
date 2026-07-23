"""Winning Profile Hypothesis™ taxonomy — the explainable knowledge base.

This module is the *only* place domain knowledge is encoded. Two structures:

1. ``SIGNAL_LEXICON`` — how raw evidence text maps to classified acquisition
   signals (deterministic, keyword/phrase driven, source of truth = the words in
   the document).
2. ``ATTRIBUTE_LIBRARY`` — how classified signals fuse into candidate winning-
   profile attributes, and how a contractor's capabilities map onto those same
   attributes for alignment scoring.

Keeping this declarative makes the engine auditable: a reviewer can trace exactly
which phrases produced which signal, and which signals produced which attribute.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .constants import SignalCategory

# High-value document types carry more evidentiary weight (per CIOS: Q&A responses
# and Section M reveal true evaluation emphasis).
DOCUMENT_EVIDENCE_VALUE: dict[str, float] = {
    "section_m": 1.5,
    "evaluation_criteria": 1.4,
    "qa_response": 1.4,
    "government_response": 1.35,
    "section_l": 1.25,
    "final_solicitation": 1.2,
    "sources_sought": 1.15,
    "rfi": 1.1,
    "draft_rfp": 1.1,
    "statement_of_work": 1.1,
    "performance_work_statement": 1.1,
    "statement_of_objectives": 1.1,
    "historical_award": 1.2,
    "incumbent_info": 1.15,
    "industry_day": 1.1,
    "agency_strategy": 1.15,
    "procurement_forecast": 1.05,
    "amendment": 1.1,
    "attachment": 1.0,
    "contract_vehicle": 1.0,
    "other": 0.9,
}


@dataclass(frozen=True)
class SignalPattern:
    """Maps evidence phrases to a classified signal category."""

    category: SignalCategory
    keywords: tuple[str, ...]
    base_strength: float  # 0–100 intrinsic strength when matched
    interpretation: str


# Ordered: the lexicon is scanned per sentence; every matching pattern fires.
SIGNAL_LEXICON: tuple[SignalPattern, ...] = (
    SignalPattern(
        SignalCategory.TRANSITION_RISK,
        (
            "transition",
            "phase-in",
            "phase in",
            "onboarding",
            "continuity of operations",
            "no disruption",
            "seamless",
            "ramp-up",
            "ramp up",
            "knowledge transfer",
        ),
        80.0,
        "Government is concerned about transition/continuity risk; low-risk phase-in "
        "capability is likely to be rewarded.",
    ),
    SignalPattern(
        SignalCategory.INCUMBENT_ADVANTAGE,
        ("incumbent", "current contractor", "existing contract", "predecessor contract"),
        70.0,
        "An incumbent is present; institutional knowledge and prior access are a factor.",
    ),
    SignalPattern(
        SignalCategory.PAST_PERFORMANCE_EMPHASIS,
        (
            "past performance",
            "cpars",
            "relevant experience",
            "demonstrated experience",
            "recency and relevancy",
            "corporate experience",
            "references",
        ),
        75.0,
        "Past performance is an explicit evaluation factor; relevant, recent CPARS matter.",
    ),
    SignalPattern(
        SignalCategory.SECURITY_REQUIREMENT,
        (
            "security clearance",
            "top secret",
            "ts/sci",
            "secret clearance",
            "facility clearance",
            "fcl",
            "cmmc",
            "nist 800-171",
            "fedramp",
            "classified",
            "cui",
            "personnel security",
        ),
        85.0,
        "Security/clearance requirements gate eligibility; cleared personnel or facilities "
        "are prerequisites.",
    ),
    SignalPattern(
        SignalCategory.PRICE_SENSITIVITY,
        (
            "lowest price",
            "lpta",
            "price reasonableness",
            "cost realism",
            "best value",
            "price competitive",
            "cost-effective",
            "affordability",
        ),
        70.0,
        "Price is a meaningful evaluation lever; cost competitiveness affects positioning.",
    ),
    SignalPattern(
        SignalCategory.KEY_PERSONNEL,
        (
            "key personnel",
            "program manager",
            "project manager",
            "named personnel",
            "resume",
            "labor category",
            "certified",
            "pmp",
            "key staff",
        ),
        72.0,
        "Named/qualified key personnel are evaluated; specific credentials are expected.",
    ),
    SignalPattern(
        SignalCategory.STAFFING_REQUIREMENT,
        (
            "full-time equivalent",
            "fte",
            "staffing plan",
            "level of effort",
            "labor hours",
            "recruit",
            "retention",
            "workforce",
        ),
        60.0,
        "Staffing depth and a credible workforce plan are required.",
    ),
    SignalPattern(
        SignalCategory.SCALE_CAPACITY,
        (
            "nationwide",
            "enterprise-wide",
            "surge",
            "scalability",
            "large scale",
            "multiple locations",
            "24/7",
            "high volume",
            "capacity",
        ),
        65.0,
        "Scale and surge capacity are required; small-capacity firms are disadvantaged.",
    ),
    SignalPattern(
        SignalCategory.TECHNICAL_COMPLEXITY,
        (
            "technical approach",
            "system integration",
            "architecture",
            "engineering",
            "complex",
            "technical solution",
            "sophisticated",
            "cloud migration",
            "data analytics",
            "cybersecurity",
        ),
        68.0,
        "Technical solution depth is central; a credible, detailed approach is expected.",
    ),
    SignalPattern(
        SignalCategory.INNOVATION_EMPHASIS,
        (
            "innovation",
            "modernization",
            "emerging technology",
            "artificial intelligence",
            "machine learning",
            "automation",
            "digital transformation",
            "novel approach",
        ),
        62.0,
        "Government seeks innovation/modernization; differentiated approaches are rewarded.",
    ),
    SignalPattern(
        SignalCategory.DOMAIN_EXPERTISE,
        (
            "subject matter expert",
            "domain expertise",
            "mission knowledge",
            "agency mission",
            "specialized knowledge",
            "deep understanding",
            "sme",
        ),
        70.0,
        "Deep domain/mission expertise is expected; generalists are disadvantaged.",
    ),
    SignalPattern(
        SignalCategory.COMPLIANCE_REQUIREMENT,
        (
            "iso 9001",
            "cmmi",
            "section 508",
            "accessibility",
            "regulatory compliance",
            "quality management",
            "far compliance",
            "certification required",
            "compliance with",
        ),
        58.0,
        "Formal compliance/quality certifications are required or strongly preferred.",
    ),
    SignalPattern(
        SignalCategory.SMALL_BUSINESS_PREFERENCE,
        (
            "small business set-aside",
            "set-aside",
            "set aside",
            "sole source small business",
            "8(a) set-aside",
            "8(a) sole source",
            "sdvosb set-aside",
            "hubzone set-aside",
            "wosb set-aside",
            "total small business set-aside",
            "restricted to small business",
            "reserved exclusively for small business",
        ),
        78.0,
        "The procurement itself is set aside for a socioeconomic category — this gates who "
        "may serve as prime; only qualifying firms may compete (others must team as a sub).",
    ),
    SignalPattern(
        SignalCategory.SMALL_BUSINESS_SUBCONTRACTING,
        (
            "small business participation",
            "small business subcontracting",
            "subcontracting plan",
            "subcontracting goal",
            "small business utilization",
            "participation commitment",
            "small disadvantaged business",
            "8(a)",
            "8a",
            "sdvosb",
            "hubzone",
            "wosb",
            "small business",
            "socioeconomic",
        ),
        50.0,
        "A small-business subcontracting participation plan or goal is expected — this is a "
        "compliance obligation typically placed on large-business primes, not a gate on who "
        "may bid as prime.",
    ),
    SignalPattern(
        SignalCategory.SCHEDULE_PRESSURE,
        (
            "aggressive schedule",
            "tight timeline",
            "immediate",
            "expedited",
            "urgent",
            "short turnaround",
            "accelerated",
            "period of performance begins",
        ),
        60.0,
        "Schedule pressure elevates the value of a ready, low-risk offeror.",
    ),
    SignalPattern(
        SignalCategory.GEOGRAPHIC_REQUIREMENT,
        (
            "on-site",
            "on site",
            "place of performance",
            "local presence",
            "within",
            "co-located",
            "government facility",
            "region",
        ),
        50.0,
        "On-site/geographic presence is required; local footprint helps.",
    ),
    SignalPattern(
        SignalCategory.AGENCY_PRIORITY,
        (
            "strategic priority",
            "agency goal",
            "mission critical",
            "highest priority",
            "administration priority",
            "executive order",
            "strategic objective",
        ),
        66.0,
        "The buy advances an explicit agency/administration priority; mission alignment matters.",
    ),
    SignalPattern(
        SignalCategory.EVALUATION_EMPHASIS,
        (
            "most important",
            "significantly more important",
            "weighted",
            "evaluation factor",
            "adjectival rating",
            "technically acceptable",
            "trade-off",
            "tradeoff",
            "factors are",
            "in descending order",
        ),
        72.0,
        "Explicit evaluation weighting signals where the government will discriminate.",
    ),
    SignalPattern(
        SignalCategory.REQUIREMENT_AMBIGUITY,
        (
            "to be determined",
            "tbd",
            "further guidance",
            "will be provided later",
            "not yet defined",
            "under development",
            "clarification",
        ),
        45.0,
        "Requirement ambiguity signals flexibility and risk; adaptable offerors benefit.",
    ),
    SignalPattern(
        SignalCategory.SHAPING_RISK,
        (
            "brand name or equal",
            "salient characteristics",
            "justification for other than full and open competition",
            "jofoc",
            "sole source",
            "only one responsible source",
            "single responsible source",
            "proprietary system",
            "specific make and model",
            "particular manufacturer",
            "exclusively compatible with",
        ),
        80.0,
        "Language associated with narrowly tailored or single-source requirements is "
        "present. The requirement may have been shaped around a specific incumbent or "
        "vendor rather than reflecting full and open competition — read the resulting "
        "hypothesis as a description of the written record, not confirmation the "
        "competition is open.",
    ),
    SignalPattern(
        SignalCategory.VEHICLE_OPEN_COMPETITION,
        (
            "multiple-award idiq",
            "multiple award idiq",
            "multiple-award contract",
            "on-ramping",
            "periodic on-ramping",
            "open season",
            "rolling admission",
            "gwac",
            "multi-agency contract",
            "unrestricted pool",
            "additional awardees may be added",
            "unlimited number of awards",
            "welcomes new entrants",
            "open to new entrants",
        ),
        75.0,
        "Language associated with a genuinely open, multi-award contract vehicle is "
        "present — one that periodically admits new awardees rather than closing the "
        "pool at initial award. This is a base-vehicle-level read (is the seat itself "
        "contestable), separate from whether any given task order under it is "
        "competed.",
    ),
    SignalPattern(
        SignalCategory.VEHICLE_NARROWING,
        (
            "single-award idiq",
            "single award idiq",
            "closed to new entrants",
            "no additional on-ramp",
            "bridge contract",
            "interim contract vehicle",
            "sole-source vehicle",
            "limited to current awardees",
            "limited to incumbent awardees",
            "existing awardee pool only",
            "closed pool",
            "no further awardees will be added",
        ),
        75.0,
        "Language associated with a narrow, closed, or single-award contract vehicle "
        "is present — one where the awardee pool is fixed and not open to new "
        "entrants. A base-vehicle-level read: B&P investment aimed at winning a new "
        "seat on this vehicle is unlikely to pay off; value would instead concentrate "
        "on task orders under vehicles already held.",
    ),
)


@dataclass(frozen=True)
class AttributeDef:
    """A candidate winning-profile attribute and how evidence fuses into it."""

    key: str  # stable identifier used for contractor matching
    name: str
    category: str  # capability dimension
    description: str
    base_importance: float  # intrinsic prior weight (0–100 pre-normalization)
    driving_signals: tuple[SignalCategory, ...]
    # Keywords used to locate this capability inside a contractor's free-text profile.
    capability_keywords: tuple[str, ...] = field(default_factory=tuple)


# The universe of attributes the engine can infer. Only attributes with at least
# one supporting signal are emitted into a Winning Profile Hypothesis.
ATTRIBUTE_LIBRARY: tuple[AttributeDef, ...] = (
    AttributeDef(
        "transition_capability",
        "Low-Risk Transition Capability",
        "transition",
        "Proven ability to phase in and assume operations without disruption to the mission.",
        14.0,
        (
            SignalCategory.TRANSITION_RISK,
            SignalCategory.INCUMBENT_ADVANTAGE,
            SignalCategory.SCHEDULE_PRESSURE,
        ),
        ("transition", "phase-in", "onboarding", "continuity", "knowledge transfer"),
    ),
    AttributeDef(
        "relevant_past_performance",
        "Relevant & Recent Past Performance",
        "past_performance",
        "A portfolio of recent, relevant contracts of similar size, scope, and complexity.",
        16.0,
        (
            SignalCategory.PAST_PERFORMANCE_EMPHASIS,
            SignalCategory.EVALUATION_EMPHASIS,
            SignalCategory.INCUMBENT_ADVANTAGE,
        ),
        ("past performance", "cpars", "contract", "delivered", "prime", "experience"),
    ),
    AttributeDef(
        "security_posture",
        "Security & Clearance Posture",
        "security",
        "Cleared personnel, facility clearance, and cyber/compliance accreditations in place.",
        14.0,
        (SignalCategory.SECURITY_REQUIREMENT, SignalCategory.COMPLIANCE_REQUIREMENT),
        ("clearance", "cleared", "ts/sci", "secret", "fcl", "cmmc", "fedramp", "nist"),
    ),
    AttributeDef(
        "technical_solution_depth",
        "Technical Solution Depth",
        "technical",
        "A credible, detailed, low-risk technical approach demonstrating engineering depth.",
        13.0,
        (SignalCategory.TECHNICAL_COMPLEXITY, SignalCategory.INNOVATION_EMPHASIS),
        (
            "engineering",
            "architecture",
            "integration",
            "cloud",
            "cybersecurity",
            "analytics",
            "software",
            "devsecops",
        ),
    ),
    AttributeDef(
        "domain_mission_expertise",
        "Domain & Mission Expertise",
        "domain",
        "Deep, specialized understanding of the agency's mission and operating environment.",
        11.0,
        (SignalCategory.DOMAIN_EXPERTISE, SignalCategory.AGENCY_PRIORITY),
        ("mission", "domain", "subject matter expert", "sme", "specialized"),
    ),
    AttributeDef(
        "qualified_key_personnel",
        "Qualified Key Personnel",
        "personnel",
        "Named, credentialed key personnel (e.g. PMP-certified PM) meeting labor-category needs.",
        11.0,
        (SignalCategory.KEY_PERSONNEL, SignalCategory.STAFFING_REQUIREMENT),
        ("program manager", "pmp", "certified", "key personnel", "staff", "resume"),
    ),
    AttributeDef(
        "staffing_scale",
        "Staffing Scale & Surge Capacity",
        "capacity",
        "Workforce depth and recruiting/retention pipeline to staff and surge at required scale.",
        9.0,
        (SignalCategory.SCALE_CAPACITY, SignalCategory.STAFFING_REQUIREMENT),
        ("nationwide", "surge", "workforce", "recruiting", "scale", "capacity", "ftes"),
    ),
    AttributeDef(
        "cost_competitiveness",
        "Cost Competitiveness",
        "price",
        "A competitive, realistic cost structure aligned to the evaluation's price sensitivity.",
        10.0,
        (SignalCategory.PRICE_SENSITIVITY,),
        ("competitive rates", "cost", "efficient", "affordable", "price", "low overhead"),
    ),
    AttributeDef(
        "set_aside_eligibility",
        "Set-Aside / Socioeconomic Eligibility",
        "eligibility",
        "Qualifying socioeconomic status (e.g. 8(a), SDVOSB, HUBZone) matching the set-aside.",
        12.0,
        (SignalCategory.SMALL_BUSINESS_PREFERENCE,),
        ("8(a)", "8a", "sdvosb", "hubzone", "wosb", "small business", "set-aside"),
    ),
    AttributeDef(
        "small_business_subcontracting_plan",
        "Small Business Subcontracting Plan Compliance",
        "subcontracting",
        "A FAR 52.219-9-compliant plan (or demonstrated track record) for meeting small-business "
        "subcontracting participation goals — a compliance obligation for large-business primes "
        "on full-and-open awards, not an eligibility gate on who may bid.",
        9.0,
        (SignalCategory.SMALL_BUSINESS_SUBCONTRACTING,),
        (
            "subcontracting plan",
            "small business utilization",
            "subcontracting goal",
            "far 52.219-9",
            "small business participation",
        ),
    ),
    AttributeDef(
        "compliance_readiness",
        "Regulatory & Compliance Readiness",
        "compliance",
        "Formal quality/compliance certifications (CMMI, ISO 9001, 508) and mature processes.",
        8.0,
        (SignalCategory.COMPLIANCE_REQUIREMENT,),
        ("cmmi", "iso 9001", "iso9001", "508", "quality management", "accredited"),
    ),
    AttributeDef(
        "innovation_modernization",
        "Innovation & Modernization Capability",
        "innovation",
        "Demonstrated modernization/innovation (AI, automation, digital transformation).",
        8.0,
        (SignalCategory.INNOVATION_EMPHASIS,),
        ("innovation", "modernization", "ai", "machine learning", "automation", "digital"),
    ),
    AttributeDef(
        "geographic_presence",
        "Geographic / On-Site Presence",
        "geographic",
        "Local footprint or on-site presence at the place of performance.",
        6.0,
        (SignalCategory.GEOGRAPHIC_REQUIREMENT,),
        ("on-site", "local", "office", "presence", "regional"),
    ),
)

# Fast lookup by driving signal category → attributes it contributes to.
_ATTR_BY_SIGNAL: dict[SignalCategory, list[AttributeDef]] = {}
for _attr in ATTRIBUTE_LIBRARY:
    for _sig in _attr.driving_signals:
        _ATTR_BY_SIGNAL.setdefault(_sig, []).append(_attr)


def attributes_for_signal(category: SignalCategory | str) -> list[AttributeDef]:
    """Return attribute definitions driven by a given signal category."""
    if isinstance(category, str):
        try:
            category = SignalCategory(category)
        except ValueError:
            return []
    return _ATTR_BY_SIGNAL.get(category, [])
