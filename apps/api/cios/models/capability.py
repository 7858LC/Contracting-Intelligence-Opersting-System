"""Capability and Gap Analysis models — Modules 5 & 15."""
from sqlalchemy import Float, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from cios.core.database import Base
from .base import UUIDMixin, TimestampMixin, TenantMixin, EvidenceMixin


class Capability(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "capabilities"
    __table_args__ = (
        Index("idx_cap_tenant_category", "tenant_id", "category"),
    )

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    maturity_level: Mapped[str | None] = mapped_column(String(32))
    proficiency_score: Mapped[float | None] = mapped_column(Float)
    supporting_evidence: Mapped[list] = mapped_column(JSONB, default=list)
    naics_codes: Mapped[list] = mapped_column(JSONB, default=list)
    psc_codes: Mapped[list] = mapped_column(JSONB, default=list)
    certifications: Mapped[list] = mapped_column(JSONB, default=list)
    tools_and_technologies: Mapped[list] = mapped_column(JSONB, default=list)
    team_members_count: Mapped[int | None] = mapped_column()
    last_demonstrated: Mapped[str | None] = mapped_column(String(64))


class CapabilityGap(Base, UUIDMixin, TimestampMixin, TenantMixin, EvidenceMixin):
    __tablename__ = "capability_gaps"

    opportunity_id: Mapped[str | None] = mapped_column(String(64))
    gap_name: Mapped[str] = mapped_column(String(256), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    description: Mapped[str | None] = mapped_column(Text)
    remediation_options: Mapped[list] = mapped_column(JSONB, default=list)
    estimated_cost_to_close: Mapped[float | None] = mapped_column(Float)
    estimated_time_to_close_days: Mapped[int | None] = mapped_column()
    teaming_recommendation: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="open")
