"""Teaming Recommendation Engine models — Module 7."""
import uuid
from sqlalchemy import Boolean, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from cios.core.database import Base
from .base import UUIDMixin, TimestampMixin, TenantMixin, EvidenceMixin


class TeamingRecommendation(Base, UUIDMixin, TimestampMixin, TenantMixin, EvidenceMixin):
    __tablename__ = "teaming_recommendations"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    prime_or_sub: Mapped[str] = mapped_column(String(16), default="prime")
    rationale: Mapped[str | None] = mapped_column(Text)
    team_structure: Mapped[dict] = mapped_column(JSONB, default=dict)
    capability_gaps_addressed: Mapped[list] = mapped_column(JSONB, default=list)
    recommended_partners: Mapped[list] = mapped_column(JSONB, default=list)
    risk_assessment: Mapped[dict | None] = mapped_column(JSONB)
    win_probability_impact: Mapped[float | None] = mapped_column(Float)
    risks: Mapped[list] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(32), default="draft")


class TeamingPartner(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "teaming_partners"
    __table_args__ = (
        Index("idx_tp_tenant", "tenant_id"),
    )

    company_name: Mapped[str] = mapped_column(String(256), nullable=False)
    cage_code: Mapped[str | None] = mapped_column(String(8))
    duns_number: Mapped[str | None] = mapped_column(String(13))
    sam_unique_id: Mapped[str | None] = mapped_column(String(64))
    website: Mapped[str | None] = mapped_column(String(512))
    naics_codes: Mapped[list] = mapped_column(JSONB, default=list)
    psc_codes: Mapped[list] = mapped_column(JSONB, default=list)
    capabilities: Mapped[list] = mapped_column(JSONB, default=list)
    socioeconomic_status: Mapped[list] = mapped_column(JSONB, default=list)
    past_performance_rating: Mapped[int | None] = mapped_column(Integer)
    active_agreements: Mapped[bool] = mapped_column(Boolean, default=False)
    relationship_strength: Mapped[int] = mapped_column(Integer, default=3)
    poc_name: Mapped[str | None] = mapped_column(String(256))
    poc_email: Mapped[str | None] = mapped_column(String(256))
    notes: Mapped[str | None] = mapped_column(Text)
    ai_compatibility_score: Mapped[float | None] = mapped_column(Float)
