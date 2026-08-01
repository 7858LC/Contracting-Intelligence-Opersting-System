"""Capability and Gap Analysis models — Modules 5 & 15."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from cios.core.database import Base

from .base import EvidenceMixin, TenantMixin, TimestampMixin, UUIDMixin


class Capability(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "capabilities"
    __table_args__ = (Index("idx_cap_tenant_category", "tenant_id", "category"),)

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    proficiency_level: Mapped[int | None] = mapped_column(Integer)
    proficiency_score: Mapped[float | None] = mapped_column(Float)
    maturity_level: Mapped[str | None] = mapped_column(String(32))
    is_certified: Mapped[bool] = mapped_column(Boolean, default=False)
    certifications: Mapped[list] = mapped_column(JSONB, default=list)
    gap_score: Mapped[float | None] = mapped_column(Float)
    gap_analysis: Mapped[dict | None] = mapped_column(JSONB)
    improvement_plan: Mapped[str | None] = mapped_column(Text)
    supporting_evidence: Mapped[list] = mapped_column(JSONB, default=list)
    naics_codes: Mapped[list] = mapped_column(JSONB, default=list)
    psc_codes: Mapped[list] = mapped_column(JSONB, default=list)
    tools_and_technologies: Mapped[list] = mapped_column(JSONB, default=list)
    team_members_count: Mapped[int | None] = mapped_column(Integer)
    last_demonstrated: Mapped[str | None] = mapped_column(String(64))


class CapabilityGapAnalysisRun(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Tracks one run of run_capability_gap_analysis for an opportunity.

    Same status/error_message pattern as CompetitiveLandscapeAnalysis
    (models/competitor.py) and award_simulations: distinguishes "never run"
    from "ran and found nothing to report" from "silently failed" — a bare
    empty CapabilityGap list for an opportunity is ambiguous on its own
    (no WPH profile yet vs. genuinely zero gaps), so the run record is the
    thing the frontend actually polls.
    """

    __tablename__ = "capability_gap_analysis_runs"
    __table_args__ = (Index("idx_cgar_tenant_opp", "tenant_id", "opportunity_id"),)

    opportunity_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    solicitation_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)
    gap_count: Mapped[int | None] = mapped_column(Integer)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CapabilityGap(Base, UUIDMixin, TimestampMixin, TenantMixin, EvidenceMixin):
    __tablename__ = "capability_gaps"

    analysis_run_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("capability_gap_analysis_runs.id", ondelete="CASCADE"),
        index=True,
    )
    opportunity_id: Mapped[str | None] = mapped_column(String(64))
    gap_name: Mapped[str] = mapped_column(String(256), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    description: Mapped[str | None] = mapped_column(Text)
    remediation_options: Mapped[list] = mapped_column(JSONB, default=list)
    estimated_cost_to_close: Mapped[float | None] = mapped_column(Float)
    estimated_time_to_close_days: Mapped[int | None] = mapped_column(Integer)
    teaming_recommendation: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="open")
