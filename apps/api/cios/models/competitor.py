"""Competitive Intelligence models — Module 8."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from cios.core.database import Base

from .base import EvidenceMixin, TenantMixin, TimestampMixin, UUIDMixin


class Competitor(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "competitors"
    __table_args__ = (Index("idx_comp_tenant", "tenant_id"),)

    company_name: Mapped[str] = mapped_column(String(256), nullable=False)
    cage_code: Mapped[str | None] = mapped_column(String(8))
    duns_number: Mapped[str | None] = mapped_column(String(13))
    naics_codes: Mapped[list] = mapped_column(JSONB, default=list)
    capabilities_summary: Mapped[str | None] = mapped_column(Text)
    known_strengths: Mapped[list] = mapped_column(JSONB, default=list)
    known_weaknesses: Mapped[list] = mapped_column(JSONB, default=list)
    win_rate_estimate: Mapped[float | None] = mapped_column(Float)
    annual_contract_volume: Mapped[float | None] = mapped_column(Float)
    past_awards: Mapped[list] = mapped_column(JSONB, default=list)
    agency_relationships: Mapped[list] = mapped_column(JSONB, default=list)
    pricing_tendency: Mapped[str | None] = mapped_column(String(32))
    threat_level: Mapped[str] = mapped_column(String(16), default="medium")
    socioeconomic_statuses: Mapped[list] = mapped_column(JSONB, default=list)
    active_clearances: Mapped[list] = mapped_column(JSONB, default=list)
    certifications: Mapped[list] = mapped_column(JSONB, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list] = mapped_column(JSONB, default=list)


class CompetitorIntelligence(Base, UUIDMixin, TimestampMixin, TenantMixin, EvidenceMixin):
    __tablename__ = "competitor_intelligence"

    competitor_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    intel_type: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(String(256))
    source_url: Mapped[str | None] = mapped_column(String(2048))
    relevance_score: Mapped[float | None] = mapped_column(Float)
    is_verified: Mapped[bool | None] = mapped_column(Boolean)


class CompetitiveLandscapeAnalysis(Base, UUIDMixin, TimestampMixin, TenantMixin, EvidenceMixin):
    """Computed output of run_competitive_analysis for one opportunity —
    the front-runner (highest WPHAlignment rank, excluding is_self) plus the
    next tiers, each enriched with the tenant's tracked Competitor intel
    where a link exists (see WPHContractor.competitor_id, migration 020).

    status/error_message follow the same "never run" vs. "ran and failed"
    vs. "completed" distinction as award_simulations/pir_ai_analyses —
    without it, a missing WPH solicitation/profile/alignment for this
    opportunity and a genuine analysis failure would both just look like an
    opportunity with no landscape data.
    """

    __tablename__ = "competitive_landscape_analyses"
    __table_args__ = (Index("idx_cla_tenant_opp", "tenant_id", "opportunity_id"),)

    opportunity_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    solicitation_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)
    # Each of front_runner/next_tiers items: {contractor_id, contractor_name,
    # alignment_score, rank, competitor_id, threat_level, pricing_tendency,
    # known_strengths, known_weaknesses, notes}
    front_runner: Mapped[dict | None] = mapped_column(JSONB)
    next_tiers: Mapped[list] = mapped_column(JSONB, default=list)
    candidate_pool_size: Mapped[int | None] = mapped_column(Integer)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
