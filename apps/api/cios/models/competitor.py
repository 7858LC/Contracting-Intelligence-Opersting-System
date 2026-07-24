"""Competitive Intelligence models — Module 8."""

import uuid

from sqlalchemy import Boolean, Float, Index, String, Text
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
