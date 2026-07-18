"""Award Simulator model — flagship feature, Module 13."""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cios.core.database import Base
from .base import UUIDMixin, TimestampMixin, TenantMixin, EvidenceMixin


class AwardSimulation(Base, UUIDMixin, TimestampMixin, TenantMixin, EvidenceMixin):
    """
    Emulates government source selection to predict award probability
    and surface weaknesses/deficiencies before proposal submission.
    """
    __tablename__ = "award_simulations"
    __table_args__ = (
        Index("idx_sim_tenant_opp", "tenant_id", "opportunity_id"),
    )

    opportunity_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    simulation_type: Mapped[str] = mapped_column(String(64), default="full_source_selection")

    # Evaluation methodology
    evaluation_methodology: Mapped[str] = mapped_column(String(64), default="LPTA")
    source_selection_authority: Mapped[str | None] = mapped_column(String(128))
    evaluation_factors: Mapped[list[dict]] = mapped_column(JSONB, default=list)

    # Scores (0–100)
    technical_score: Mapped[float | None] = mapped_column(Float)
    management_score: Mapped[float | None] = mapped_column(Float)
    past_performance_score: Mapped[float | None] = mapped_column(Float)
    price_competitiveness_score: Mapped[float | None] = mapped_column(Float)
    small_business_score: Mapped[float | None] = mapped_column(Float)
    compliance_score: Mapped[float | None] = mapped_column(Float)
    risk_score: Mapped[float | None] = mapped_column(Float)

    # Overall
    overall_score: Mapped[float | None] = mapped_column(Float)
    award_probability: Mapped[float | None] = mapped_column(Float)

    # Findings
    weaknesses: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    significant_weaknesses: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    deficiencies: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    strengths: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    risks: Mapped[list[dict]] = mapped_column(JSONB, default=list)

    # Red team analysis
    red_team_comments: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    suggested_improvements: Mapped[list[dict]] = mapped_column(JSONB, default=list)

    # Executive output
    executive_summary: Mapped[str | None] = mapped_column(Text)
    gate_review_recommendation: Mapped[str | None] = mapped_column(String(16))

    # Competitor comparison
    competitor_analysis: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    price_to_win_estimate: Mapped[float | None] = mapped_column(Float)

    # Procurement rule applied
    rule_pack: Mapped[str] = mapped_column(String(64), default="us_federal_far")
    rule_citations: Mapped[list[dict]] = mapped_column(JSONB, default=list)

    # Execution lifecycle
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)

    sections: Mapped[list["AwardSimulationSection"]] = relationship(
        back_populates="simulation", cascade="all, delete-orphan"
    )


class AwardSimulationSection(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "award_simulation_sections"

    simulation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("award_simulations.id", ondelete="CASCADE"),
        nullable=False,
    )
    factor_name: Mapped[str] = mapped_column(String(128), nullable=False)
    factor_weight: Mapped[float] = mapped_column(Float, default=1.0)
    score: Mapped[float | None] = mapped_column(Float)
    rating: Mapped[str | None] = mapped_column(String(32))
    findings: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    color_rating: Mapped[str | None] = mapped_column(String(16))
    narrative: Mapped[str | None] = mapped_column(Text)
    adjectival_rating: Mapped[str | None] = mapped_column(String(32))

    simulation: Mapped["AwardSimulation"] = relationship(back_populates="sections")
