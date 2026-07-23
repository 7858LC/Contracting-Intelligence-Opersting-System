"""Winning Profile Hypothesis™ Engine — pre-award intelligence domain models.

This is the foundational pre-award intelligence layer of CIOS. It operationalizes
Procurement Intelligence™ by inferring — from the pre-proposal evidence package —
the characteristics an ideal awardee would most likely need, *before* proposal
development begins.

Design principle (per CIOS): evidence is the source of truth. Every inferred
attribute, alignment score, gap, and recommendation is traceable back to the
procurement signals that produced it. The engine is an explainable evidence-fusion
architecture, NOT a black-box winner-prediction model.

Pipeline (each stage persists here):
    Solicitation package (WPHSolicitation + WPHEvidenceDocument)
      → Procurement signals (WPHSignal)
      → Winning Profile Hypothesis™ (WPHProfile + WPHProfileAttribute)
      → Contractor Alignment Analysis™ / Ranking™ / Gap Analysis™ (WPHAlignment)
      → Executive Opportunity Intelligence Assessment™ + PDQ™ (WPHAssessment)
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cios.core.database import Base
from cios.wph.constants import (  # noqa: F401 — re-exported for API/task consumers
    ConfidenceLevel,
    EvidenceDocumentType,
    PipelineStatus,
    PursuitRecommendation,
    SignalCategory,
)

from .base import EvidenceMixin, TenantMixin, TimestampMixin, UUIDMixin

# ── Solicitation package ─────────────────────────────────────────────────────────


class WPHSolicitation(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """A pre-award solicitation package — the unit of analysis for the engine.

    Optionally linked to a Module-1 Opportunity, but self-contained so the engine
    can be exercised on any evidence package (e.g. a Sources Sought before the
    opportunity is tracked).
    """

    __tablename__ = "wph_solicitations"
    __table_args__ = (
        Index("idx_wph_sol_tenant_status", "tenant_id", "pipeline_status"),
        Index("idx_wph_sol_number", "solicitation_number"),
    )

    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), index=True)

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    solicitation_number: Mapped[str | None] = mapped_column(String(128))
    agency: Mapped[str | None] = mapped_column(String(256))
    sub_agency: Mapped[str | None] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text)

    naics_codes: Mapped[list] = mapped_column(JSONB, default=list)
    psc_codes: Mapped[list] = mapped_column(JSONB, default=list)
    set_aside_type: Mapped[str | None] = mapped_column(String(64))
    estimated_value: Mapped[float | None] = mapped_column(Float)
    incumbent: Mapped[str | None] = mapped_column(String(256))
    rule_pack: Mapped[str] = mapped_column(String(64), default="us_federal_far")

    pipeline_status: Mapped[str] = mapped_column(
        String(32), default=PipelineStatus.DRAFT, nullable=False
    )
    document_count: Mapped[int] = mapped_column(Integer, default=0)
    signal_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))

    documents: Mapped[list[WPHEvidenceDocument]] = relationship(
        back_populates="solicitation", cascade="all, delete-orphan", lazy="select"
    )
    signals: Mapped[list[WPHSignal]] = relationship(
        back_populates="solicitation", cascade="all, delete-orphan", lazy="select"
    )
    profiles: Mapped[list[WPHProfile]] = relationship(
        back_populates="solicitation", cascade="all, delete-orphan", lazy="select"
    )


# ── Evidence documents ───────────────────────────────────────────────────────────


class WPHEvidenceDocument(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """One document within a solicitation package (e.g. Section M, a Q&A response)."""

    __tablename__ = "wph_evidence_documents"
    __table_args__ = (
        Index("idx_wph_doc_sol", "solicitation_id"),
        Index("idx_wph_doc_type", "solicitation_id", "document_type"),
    )

    solicitation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("wph_solicitations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_type: Mapped[str] = mapped_column(String(48), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_url: Mapped[str | None] = mapped_column(String(2048))
    source_ref: Mapped[str | None] = mapped_column(String(256))
    is_extracted: Mapped[bool] = mapped_column(Boolean, default=False)
    doc_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)

    solicitation: Mapped[WPHSolicitation] = relationship(back_populates="documents")


# ── Extracted & classified procurement signals ───────────────────────────────────


class WPHSignal(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """A single classified acquisition signal extracted from an evidence document.

    Every signal preserves the *verbatim* evidence text and its source, so any
    downstream inference is auditable back to the exact document snippet.
    """

    __tablename__ = "wph_signals"
    __table_args__ = (
        Index("idx_wph_signal_sol", "solicitation_id"),
        Index("idx_wph_signal_category", "solicitation_id", "category"),
    )

    solicitation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("wph_solicitations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), index=True)

    category: Mapped[str] = mapped_column(String(48), nullable=False)
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False)
    interpretation: Mapped[str | None] = mapped_column(Text)

    # 0–100: how strongly the signal indicates its category
    strength: Mapped[float] = mapped_column(Float, default=0.0)
    # 0–100: confidence the extraction/classification is correct
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    source_document_type: Mapped[str | None] = mapped_column(String(48))
    source_ref: Mapped[str | None] = mapped_column(String(256))
    keywords: Mapped[list] = mapped_column(JSONB, default=list)
    raw: Mapped[dict] = mapped_column(JSONB, default=dict)

    solicitation: Mapped[WPHSolicitation] = relationship(back_populates="signals")


# ── Winning Profile Hypothesis™ ──────────────────────────────────────────────────


class WPHProfile(Base, UUIDMixin, TimestampMixin, TenantMixin, EvidenceMixin):
    """The Winning Profile Hypothesis™ — an explainable inference of what the ideal
    awardee would most likely look like for this acquisition. Versioned per
    solicitation; ``is_current`` marks the latest.
    """

    __tablename__ = "wph_profiles"
    __table_args__ = (
        Index("idx_wph_profile_sol", "solicitation_id"),
        Index("idx_wph_profile_current", "solicitation_id", "is_current"),
        UniqueConstraint("solicitation_id", "version", name="uq_wph_profile_version"),
    )

    solicitation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("wph_solicitations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)

    summary: Mapped[str | None] = mapped_column(Text)
    narrative: Mapped[str | None] = mapped_column(Text)  # optional Claude enrichment
    overall_confidence: Mapped[float] = mapped_column(Float, default=0.0)  # 0–100
    evidence_strength: Mapped[float] = mapped_column(Float, default=0.0)  # 0–100
    attribute_count: Mapped[int] = mapped_column(Integer, default=0)
    unknown_factors: Mapped[list] = mapped_column(JSONB, default=list)
    shaping_risk: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    vehicle_contestability: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    status: Mapped[str] = mapped_column(String(32), default="generated")
    model_used: Mapped[str | None] = mapped_column(String(64))

    solicitation: Mapped[WPHSolicitation] = relationship(back_populates="profiles")
    attributes: Mapped[list[WPHProfileAttribute]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", lazy="select"
    )


class WPHProfileAttribute(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """A single inferred attribute of the winning profile.

    Matches the CIOS Winning Profile Hypothesis data model exactly:
    name, description, importance weight, evidence confidence, supporting evidence,
    evidence source references, reasoning, unknown factors, confidence level.
    """

    __tablename__ = "wph_profile_attributes"
    __table_args__ = (
        Index("idx_wph_attr_profile", "profile_id"),
        Index("idx_wph_attr_importance", "profile_id", "importance_weight"),
    )

    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("wph_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    category: Mapped[str] = mapped_column(String(48), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    importance_weight: Mapped[float] = mapped_column(Float, default=0.0)  # 0–100
    evidence_confidence: Mapped[float] = mapped_column(Float, default=0.0)  # 0–100
    confidence_level: Mapped[str] = mapped_column(String(16), default=ConfidenceLevel.LOW)

    # Required proficiency (0–100) a candidate should demonstrate on this attribute.
    required_level: Mapped[float] = mapped_column(Float, default=70.0)

    supporting_evidence: Mapped[list] = mapped_column(JSONB, default=list)  # [{text, source}]
    evidence_source_refs: Mapped[list] = mapped_column(JSONB, default=list)
    signal_ids: Mapped[list] = mapped_column(JSONB, default=list)  # traceability
    reasoning: Mapped[str | None] = mapped_column(Text)
    unknown_factors: Mapped[list] = mapped_column(JSONB, default=list)

    profile: Mapped[WPHProfile] = relationship(back_populates="attributes")


# ── Contractor capability profiles ───────────────────────────────────────────────


class WPHContractor(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """A candidate contractor (may be the customer's own org or a competitor)
    scored against a Winning Profile Hypothesis. Tenant-scoped and reusable
    across solicitations.
    """

    __tablename__ = "wph_contractors"
    __table_args__ = (
        Index("idx_wph_contractor_tenant", "tenant_id"),
        UniqueConstraint("tenant_id", "name", name="uq_wph_contractor_name"),
    )

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    samgov_uei: Mapped[str | None] = mapped_column(String(12))
    cage_code: Mapped[str | None] = mapped_column(String(10))

    is_self: Mapped[bool] = mapped_column(Boolean, default=False)  # the customer's own org
    is_incumbent: Mapped[bool] = mapped_column(Boolean, default=False)
    business_size: Mapped[str | None] = mapped_column(String(16))  # small | large
    employee_count: Mapped[int | None] = mapped_column(Integer)

    naics_codes: Mapped[list] = mapped_column(JSONB, default=list)
    certifications: Mapped[list] = mapped_column(JSONB, default=list)
    set_asides: Mapped[list] = mapped_column(JSONB, default=list)
    clearances: Mapped[list] = mapped_column(JSONB, default=list)
    # [{name, level 0-100, evidence}] — capability inventory
    capabilities: Mapped[list] = mapped_column(JSONB, default=list)
    past_performance: Mapped[list] = mapped_column(JSONB, default=list)


# ── Contractor Alignment Analysis™ / Ranking™ / Gap Analysis™ ─────────────────────


class WPHAlignment(Base, UUIDMixin, TimestampMixin, TenantMixin, EvidenceMixin):
    """How well one contractor aligns to the Winning Profile Hypothesis.

    Carries the full auditable breakdown: per-attribute alignment, ranking,
    capability gaps, and gap-closure recommendations.
    """

    __tablename__ = "wph_alignments"
    __table_args__ = (
        Index("idx_wph_align_profile", "profile_id"),
        Index("idx_wph_align_rank", "profile_id", "rank"),
        UniqueConstraint("profile_id", "contractor_id", name="uq_wph_align_profile_contractor"),
    )

    solicitation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("wph_solicitations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("wph_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contractor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("wph_contractors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contractor_name: Mapped[str] = mapped_column(String(256), nullable=False)

    overall_alignment_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0–100
    rank: Mapped[int] = mapped_column(Integer, default=0)

    # [{attribute_name, importance_weight, required_level, contractor_level,
    #   alignment, contribution, evidence, reasoning}]
    attribute_alignments: Mapped[list] = mapped_column(JSONB, default=list)
    # [{attribute_name, category, severity, importance_weight, required_level,
    #   contractor_level, gap_size, impact}]
    gaps: Mapped[list] = mapped_column(JSONB, default=list)
    # [{gap_attribute, recommendation, action_type, effort, timeline_months,
    #   feasibility, cost_band, closes_gap_to}]
    gap_closures: Mapped[list] = mapped_column(JSONB, default=list)

    strengths: Mapped[list] = mapped_column(JSONB, default=list)
    weaknesses: Mapped[list] = mapped_column(JSONB, default=list)
    summary: Mapped[str | None] = mapped_column(Text)
    model_used: Mapped[str | None] = mapped_column(String(64))


# ── Executive Opportunity Intelligence Assessment™ + PDQ™ ─────────────────────────


class WPHAssessment(Base, UUIDMixin, TimestampMixin, TenantMixin, EvidenceMixin):
    """The executive-level output: a Pursuit Decision Quality™ score and an
    explainable Bid / No-Bid / Conditional recommendation for a target contractor.
    """

    __tablename__ = "wph_assessments"
    __table_args__ = (
        Index("idx_wph_assess_sol", "solicitation_id"),
        Index("idx_wph_assess_target", "solicitation_id", "target_contractor_id"),
    )

    solicitation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("wph_solicitations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("wph_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_contractor_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    target_contractor_name: Mapped[str | None] = mapped_column(String(256))

    pdq_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0–100
    win_positioning_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0–100
    competitive_rank: Mapped[int | None] = mapped_column(Integer)
    candidate_pool_size: Mapped[int] = mapped_column(Integer, default=0)

    recommendation: Mapped[str] = mapped_column(
        String(24), default=PursuitRecommendation.MONITOR, nullable=False
    )
    executive_summary: Mapped[str | None] = mapped_column(Text)
    narrative: Mapped[str | None] = mapped_column(Text)  # optional Claude enrichment

    key_findings: Mapped[list] = mapped_column(JSONB, default=list)
    decision_factors: Mapped[list] = mapped_column(JSONB, default=list)
    critical_gaps: Mapped[list] = mapped_column(JSONB, default=list)
    recommended_actions: Mapped[list] = mapped_column(JSONB, default=list)
    risks: Mapped[list] = mapped_column(JSONB, default=list)
    assumptions: Mapped[list] = mapped_column(JSONB, default=list)

    status: Mapped[str] = mapped_column(String(32), default="completed")
    model_used: Mapped[str | None] = mapped_column(String(64))

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "pdq_score": self.pdq_score,
            "win_positioning_score": self.win_positioning_score,
            "recommendation": self.recommendation,
            "competitive_rank": self.competitive_rank,
            "candidate_pool_size": self.candidate_pool_size,
            "executive_summary": self.executive_summary,
        }
