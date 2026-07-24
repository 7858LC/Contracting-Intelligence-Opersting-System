"""Opportunity Intelligence model — Module 1."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cios.core.database import Base

from .base import EvidenceMixin, TenantMixin, TimestampMixin, UUIDMixin


class JurisdictionType(StrEnum):
    federal = "federal"  # US federal (FAR / DFARS)
    state = "state"  # US state-level
    local = "local"  # Municipal / county
    tribal = "tribal"  # Tribal government
    international = "international"  # EU, World Bank, bilateral


class Opportunity(Base, UUIDMixin, TimestampMixin, TenantMixin, EvidenceMixin):
    __tablename__ = "opportunities"
    __table_args__ = (
        Index("idx_opp_tenant_status", "tenant_id", "status"),
        Index("idx_opp_response_deadline", "response_deadline"),
        Index("idx_opp_award_probability", "award_probability_score"),
        Index("idx_opp_search", "search_vector", postgresql_using="gin"),
        Index("idx_opp_jurisdiction_type", "tenant_id", "jurisdiction_type"),
    )

    # Identity
    external_id: Mapped[str | None] = mapped_column(String(128), index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048))
    solicitation_number: Mapped[str | None] = mapped_column(String(128), index=True)

    # Core fields
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    agency: Mapped[str | None] = mapped_column(String(256))
    sub_agency: Mapped[str | None] = mapped_column(String(256))
    office: Mapped[str | None] = mapped_column(String(256))
    jurisdiction_type: Mapped[JurisdictionType] = mapped_column(
        String(32), default=JurisdictionType.federal, nullable=False
    )

    # Classification
    naics_codes: Mapped[list] = mapped_column(JSONB, default=list)
    psc_codes: Mapped[list] = mapped_column(JSONB, default=list)
    set_aside_type: Mapped[str | None] = mapped_column(String(64))
    solicitation_type: Mapped[str | None] = mapped_column(String(64))
    contract_type: Mapped[str | None] = mapped_column(String(64))

    # Financial
    estimated_value_min: Mapped[float | None] = mapped_column(Float)
    estimated_value_max: Mapped[float | None] = mapped_column(Float)
    ceiling_value: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    # Dates
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    response_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    award_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_of_performance_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_of_performance_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # CIOS Intelligence
    status: Mapped[str] = mapped_column(String(32), default="active")
    pipeline_stage: Mapped[str] = mapped_column(String(32), default="identified")
    award_probability_score: Mapped[float | None] = mapped_column(Float)
    bid_no_bid_recommendation: Mapped[str | None] = mapped_column(String(16))
    proposal_readiness_score: Mapped[float | None] = mapped_column(Float)
    competitive_intensity: Mapped[str | None] = mapped_column(String(16))

    # Extracted intelligence
    evaluation_criteria: Mapped[list] = mapped_column(JSONB, default=list)
    key_requirements: Mapped[list] = mapped_column(JSONB, default=list)
    incumbent: Mapped[str | None] = mapped_column(String(256))
    anticipated_competitors: Mapped[list] = mapped_column(JSONB, default=list)
    procurement_rule_pack: Mapped[str] = mapped_column(String(64), default="us_federal")

    # Full-text search
    search_vector: Mapped[Any | None] = mapped_column(TSVECTOR)

    # Raw document storage reference
    raw_document_key: Mapped[str | None] = mapped_column(String(512))
    attachments: Mapped[list] = mapped_column(JSONB, default=list)

    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    watches: Mapped[list["OpportunityWatch"]] = relationship(back_populates="opportunity")
    notes: Mapped[list["OpportunityNote"]] = relationship(back_populates="opportunity")


class OpportunityWatch(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "opportunity_watches"
    __table_args__ = (Index("uq_watch", "tenant_id", "opportunity_id", "user_id", unique=True),)

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    notify_on_change: Mapped[bool] = mapped_column(Boolean, default=True)

    opportunity: Mapped["Opportunity"] = relationship(back_populates="watches")


class OpportunityNote(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "opportunity_notes"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    note_type: Mapped[str] = mapped_column(String(32), default="general")

    opportunity: Mapped["Opportunity"] = relationship(back_populates="notes")
