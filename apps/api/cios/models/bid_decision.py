"""Bid/No-Bid Engine model — Module 2."""
import uuid
from typing import Any

from sqlalchemy import Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cios.core.database import Base
from .base import UUIDMixin, TimestampMixin, TenantMixin, EvidenceMixin


class BidDecision(Base, UUIDMixin, TimestampMixin, TenantMixin, EvidenceMixin):
    __tablename__ = "bid_decisions"
    __table_args__ = (
        Index("idx_bid_decision_tenant_opp", "tenant_id", "opportunity_id"),
    )

    opportunity_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)

    # Scores (0–100)
    strategic_fit_score: Mapped[float | None] = mapped_column(Float)
    win_probability_score: Mapped[float | None] = mapped_column(Float)
    past_performance_score: Mapped[float | None] = mapped_column(Float)
    capability_match_score: Mapped[float | None] = mapped_column(Float)
    competitive_position_score: Mapped[float | None] = mapped_column(Float)
    cost_of_bid_score: Mapped[float | None] = mapped_column(Float)
    risk_score: Mapped[float | None] = mapped_column(Float)
    relationship_score: Mapped[float | None] = mapped_column(Float)

    # Weighted composite
    composite_score: Mapped[float | None] = mapped_column(Float)

    recommendation: Mapped[str | None] = mapped_column(String(16))
    recommendation_rationale: Mapped[str | None] = mapped_column(Text)

    # Human override
    human_decision: Mapped[str | None] = mapped_column(String(16))
    human_rationale: Mapped[str | None] = mapped_column(Text)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))

    # Weightings used (snapshot for auditability)
    scoring_weights: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    alternatives: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    risks: Mapped[list[dict]] = mapped_column(JSONB, default=list)

    factors: Mapped[list["BidDecisionFactor"]] = relationship(back_populates="decision")


class BidDecisionFactor(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "bid_decision_factors"

    decision_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bid_decisions.id", ondelete="CASCADE")
    )
    factor_name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    notes: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[list[dict]] = mapped_column(JSONB, default=list)

    decision: Mapped["BidDecision"] = relationship(back_populates="factors")
