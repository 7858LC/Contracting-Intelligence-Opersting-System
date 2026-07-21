"""Pure domain enumerations for the Winning Profile Hypothesis™ engine.

Kept free of any ORM/SQLAlchemy import so the evidence-fusion pipeline can be
imported and unit-tested with no database dependency. The ORM models re-export
these same enums.
"""

from __future__ import annotations

from enum import StrEnum


class EvidenceDocumentType(StrEnum):
    """The complete pre-proposal evidence package accepted by the engine."""

    SOURCES_SOUGHT = "sources_sought"
    RFI = "rfi"
    DRAFT_RFP = "draft_rfp"
    FINAL_SOLICITATION = "final_solicitation"
    STATEMENT_OF_WORK = "statement_of_work"
    PWS = "performance_work_statement"
    SOO = "statement_of_objectives"
    ATTACHMENT = "attachment"
    AMENDMENT = "amendment"
    SECTION_L = "section_l"  # Instructions to offerors
    SECTION_M = "section_m"  # Evaluation factors for award
    EVALUATION_CRITERIA = "evaluation_criteria"
    INDUSTRY_DAY = "industry_day"
    QA_RESPONSE = "qa_response"  # Pre-award questions + gov answers (high value)
    GOV_RESPONSE = "government_response"
    PROCUREMENT_FORECAST = "procurement_forecast"
    AGENCY_STRATEGY = "agency_strategy"
    HISTORICAL_AWARD = "historical_award"
    INCUMBENT_INFO = "incumbent_info"
    CONTRACT_VEHICLE = "contract_vehicle"
    OTHER = "other"


class SignalCategory(StrEnum):
    """Classified acquisition signals extracted from the evidence package."""

    EVALUATION_EMPHASIS = "evaluation_emphasis"
    TRANSITION_RISK = "transition_risk"
    INCUMBENT_ADVANTAGE = "incumbent_advantage"
    TECHNICAL_COMPLEXITY = "technical_complexity"
    SECURITY_REQUIREMENT = "security_requirement"
    PAST_PERFORMANCE_EMPHASIS = "past_performance_emphasis"
    PRICE_SENSITIVITY = "price_sensitivity"
    SMALL_BUSINESS_PREFERENCE = "small_business_preference"
    STAFFING_REQUIREMENT = "staffing_requirement"
    KEY_PERSONNEL = "key_personnel"
    SCHEDULE_PRESSURE = "schedule_pressure"
    COMPLIANCE_REQUIREMENT = "compliance_requirement"
    DOMAIN_EXPERTISE = "domain_expertise"
    INNOVATION_EMPHASIS = "innovation_emphasis"
    SCALE_CAPACITY = "scale_capacity"
    GEOGRAPHIC_REQUIREMENT = "geographic_requirement"
    REQUIREMENT_AMBIGUITY = "requirement_ambiguity"
    AGENCY_PRIORITY = "agency_priority"


class ConfidenceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PipelineStatus(StrEnum):
    DRAFT = "draft"
    EVIDENCE_READY = "evidence_ready"
    SIGNALS_EXTRACTED = "signals_extracted"
    PROFILE_GENERATED = "profile_generated"
    ALIGNMENT_SCORED = "alignment_scored"
    ASSESSED = "assessed"
    FAILED = "failed"


class PursuitRecommendation(StrEnum):
    BID = "bid"
    NO_BID = "no_bid"
    CONDITIONAL_BID = "conditional_bid"
    MONITOR = "monitor"
