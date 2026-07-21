"""Pure-domain dataclasses for the Winning Profile Hypothesis™ engine.

These are DB-agnostic so the entire evidence-fusion pipeline can be unit-tested
without a database or network. The service layer maps ORM rows to/from these.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvidenceDoc:
    document_type: str
    title: str
    content: str
    source_ref: str | None = None
    document_id: str | None = None


@dataclass
class ExtractedSignal:
    category: str
    evidence_text: str
    interpretation: str
    strength: float          # 0–100
    confidence: float        # 0–100
    source_document_type: str
    source_ref: str | None = None
    keywords: list[str] = field(default_factory=list)
    document_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "evidence_text": self.evidence_text,
            "interpretation": self.interpretation,
            "strength": round(self.strength, 2),
            "confidence": round(self.confidence, 2),
            "source_document_type": self.source_document_type,
            "source_ref": self.source_ref,
            "keywords": self.keywords,
            "document_id": self.document_id,
        }


@dataclass
class InferredAttribute:
    key: str
    name: str
    category: str
    description: str
    importance_weight: float     # 0–100, normalized to sum to 100 across the profile
    evidence_confidence: float   # 0–100
    confidence_level: str        # high | medium | low
    required_level: float        # 0–100 proficiency bar for a candidate
    supporting_evidence: list[dict] = field(default_factory=list)  # [{text, source}]
    evidence_source_refs: list[str] = field(default_factory=list)
    reasoning: str = ""
    unknown_factors: list[str] = field(default_factory=list)
    signal_categories: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "importance_weight": round(self.importance_weight, 2),
            "evidence_confidence": round(self.evidence_confidence, 2),
            "confidence_level": self.confidence_level,
            "required_level": round(self.required_level, 2),
            "supporting_evidence": self.supporting_evidence,
            "evidence_source_refs": self.evidence_source_refs,
            "reasoning": self.reasoning,
            "unknown_factors": self.unknown_factors,
            "signal_categories": self.signal_categories,
        }


@dataclass
class WinningProfile:
    summary: str
    overall_confidence: float    # 0–100
    evidence_strength: float     # 0–100
    attributes: list[InferredAttribute] = field(default_factory=list)
    unknown_factors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "overall_confidence": round(self.overall_confidence, 2),
            "evidence_strength": round(self.evidence_strength, 2),
            "attribute_count": len(self.attributes),
            "attributes": [a.to_dict() for a in self.attributes],
            "unknown_factors": self.unknown_factors,
        }


@dataclass
class ContractorProfile:
    name: str
    description: str = ""
    is_self: bool = False
    is_incumbent: bool = False
    business_size: str | None = None
    certifications: list[str] = field(default_factory=list)
    set_asides: list[str] = field(default_factory=list)
    clearances: list[str] = field(default_factory=list)
    # Explicit capability levels keyed by attribute key OR free-form name → 0–100.
    capabilities: dict[str, float] = field(default_factory=dict)
    capability_text: str = ""  # free-text scanned for capability keywords
    past_performance: list[dict] = field(default_factory=list)


@dataclass
class AttributeAlignment:
    attribute_key: str
    attribute_name: str
    category: str
    importance_weight: float
    required_level: float
    contractor_level: float
    alignment: float          # 0–100 (% of requirement met, capped)
    contribution: float       # weighted contribution to overall score
    evidence: str = ""
    reasoning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "attribute_key": self.attribute_key,
            "attribute_name": self.attribute_name,
            "category": self.category,
            "importance_weight": round(self.importance_weight, 2),
            "required_level": round(self.required_level, 2),
            "contractor_level": round(self.contractor_level, 2),
            "alignment": round(self.alignment, 2),
            "contribution": round(self.contribution, 2),
            "evidence": self.evidence,
            "reasoning": self.reasoning,
        }


@dataclass
class CapabilityGap:
    attribute_key: str
    attribute_name: str
    category: str
    severity: str             # critical | major | moderate | minor
    importance_weight: float
    required_level: float
    contractor_level: float
    gap_size: float           # required - contractor (positive)
    impact: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "attribute_key": self.attribute_key,
            "attribute_name": self.attribute_name,
            "category": self.category,
            "severity": self.severity,
            "importance_weight": round(self.importance_weight, 2),
            "required_level": round(self.required_level, 2),
            "contractor_level": round(self.contractor_level, 2),
            "gap_size": round(self.gap_size, 2),
            "impact": self.impact,
        }


@dataclass
class GapClosure:
    gap_attribute_key: str
    gap_attribute_name: str
    recommendation: str
    action_type: str          # teaming | hire | invest | certify | partner | reprice | pursue
    effort: str               # low | medium | high
    timeline_months: int
    feasibility: str          # high | medium | low
    cost_band: str            # $ | $$ | $$$
    closes_gap_to: float      # projected contractor_level after action

    def to_dict(self) -> dict[str, Any]:
        return {
            "gap_attribute_key": self.gap_attribute_key,
            "gap_attribute_name": self.gap_attribute_name,
            "recommendation": self.recommendation,
            "action_type": self.action_type,
            "effort": self.effort,
            "timeline_months": self.timeline_months,
            "feasibility": self.feasibility,
            "cost_band": self.cost_band,
            "closes_gap_to": round(self.closes_gap_to, 2),
        }


@dataclass
class ContractorAlignment:
    contractor_name: str
    overall_alignment_score: float   # 0–100
    rank: int = 0
    attribute_alignments: list[AttributeAlignment] = field(default_factory=list)
    gaps: list[CapabilityGap] = field(default_factory=list)
    gap_closures: list[GapClosure] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "contractor_name": self.contractor_name,
            "overall_alignment_score": round(self.overall_alignment_score, 2),
            "rank": self.rank,
            "attribute_alignments": [a.to_dict() for a in self.attribute_alignments],
            "gaps": [g.to_dict() for g in self.gaps],
            "gap_closures": [c.to_dict() for c in self.gap_closures],
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "summary": self.summary,
        }


@dataclass
class Assessment:
    pdq_score: float                 # 0–100 Pursuit Decision Quality
    win_positioning_score: float     # 0–100
    recommendation: str              # bid | no_bid | conditional_bid | monitor
    competitive_rank: int | None
    candidate_pool_size: int
    executive_summary: str
    key_findings: list[str] = field(default_factory=list)
    decision_factors: list[dict] = field(default_factory=list)
    critical_gaps: list[dict] = field(default_factory=list)
    recommended_actions: list[dict] = field(default_factory=list)
    risks: list[dict] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pdq_score": round(self.pdq_score, 2),
            "win_positioning_score": round(self.win_positioning_score, 2),
            "recommendation": self.recommendation,
            "competitive_rank": self.competitive_rank,
            "candidate_pool_size": self.candidate_pool_size,
            "executive_summary": self.executive_summary,
            "key_findings": self.key_findings,
            "decision_factors": self.decision_factors,
            "critical_gaps": self.critical_gaps,
            "recommended_actions": self.recommended_actions,
            "risks": self.risks,
            "assumptions": self.assumptions,
        }
