"""Past Performance Intelligence model — Module 6."""
from sqlalchemy import Boolean, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from cios.core.database import Base
from .base import UUIDMixin, TimestampMixin, TenantMixin, EvidenceMixin


class PastPerformance(Base, UUIDMixin, TimestampMixin, TenantMixin, EvidenceMixin):
    __tablename__ = "past_performances"
    __table_args__ = (
        Index("idx_pp_tenant_type", "tenant_id", "contract_type"),
        Index("idx_pp_relevance", "relevance_score"),
    )

    # Contract details
    contract_number: Mapped[str | None] = mapped_column(String(128), index=True)
    contract_title: Mapped[str] = mapped_column(String(512), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(256), nullable=False)
    customer_agency: Mapped[str | None] = mapped_column(String(256))
    contract_type: Mapped[str | None] = mapped_column(String(64))
    contract_value: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    period_start: Mapped[str | None] = mapped_column(String(32))
    period_end: Mapped[str | None] = mapped_column(String(32))

    # Performance narrative
    scope_of_work: Mapped[str | None] = mapped_column(Text)
    key_accomplishments: Mapped[list] = mapped_column(JSONB, default=list)
    challenges_overcome: Mapped[list] = mapped_column(JSONB, default=list)
    outcomes: Mapped[list] = mapped_column(JSONB, default=list)
    metrics: Mapped[list] = mapped_column(JSONB, default=list)

    # Relevance scoring (AI-generated)
    relevance_score: Mapped[float | None] = mapped_column(Float)
    relevance_factors: Mapped[list] = mapped_column(JSONB, default=list)
    naics_codes: Mapped[list] = mapped_column(JSONB, default=list)
    psc_codes: Mapped[list] = mapped_column(JSONB, default=list)

    # CPARS / ratings
    cpars_rating: Mapped[str | None] = mapped_column(String(32))
    quality_rating: Mapped[float | None] = mapped_column(Float)
    schedule_rating: Mapped[float | None] = mapped_column(Float)
    cost_rating: Mapped[float | None] = mapped_column(Float)
    management_rating: Mapped[float | None] = mapped_column(Float)

    # Reference
    poc_name: Mapped[str | None] = mapped_column(String(256))
    poc_email: Mapped[str | None] = mapped_column(String(256))
    poc_phone: Mapped[str | None] = mapped_column(String(32))

    # Teaming
    prime_or_sub: Mapped[str] = mapped_column(String(16), default="prime")
    teaming_partners: Mapped[list] = mapped_column(JSONB, default=list)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_confidential: Mapped[bool] = mapped_column(Boolean, default=False)


class PastPerformanceTag(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "past_performance_tags"

    past_performance_id: Mapped[str] = mapped_column(String(64), nullable=False)
    tag: Mapped[str] = mapped_column(String(64), nullable=False)
    tag_type: Mapped[str] = mapped_column(String(32), default="capability")
