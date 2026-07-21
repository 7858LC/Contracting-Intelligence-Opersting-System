"""Procurement Intelligence Radar™ (PIR) — Module 0: Company Discovery & Signal Detection."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
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

from .base import EvidenceMixin, TenantMixin, TimestampMixin, UUIDMixin


class SignalType(StrEnum):
    # Hiring signals
    HIRING_CAPTURE_MANAGER = "hiring_capture_manager"
    HIRING_PROPOSAL_MANAGER = "hiring_proposal_manager"
    HIRING_BD_DIRECTOR = "hiring_bd_director"
    HIRING_CONTRACTS_MANAGER = "hiring_contracts_manager"
    HIRING_PRICING_MANAGER = "hiring_pricing_manager"
    HIRING_COMPLIANCE_MANAGER = "hiring_compliance_manager"
    HIRING_GOVERNMENT_SALES = "hiring_government_sales"
    HIRING_PROGRAM_MANAGER = "hiring_program_manager"
    HIRING_CLEARED_PERSONNEL = "hiring_cleared_personnel"
    # Award signals
    FEDERAL_CONTRACT_AWARD = "federal_contract_award"
    STATE_CONTRACT_AWARD = "state_contract_award"
    IDIQ_AWARD = "idiq_award"
    GWAC_AWARD = "gwac_award"
    SBIR_STTR_AWARD = "sbir_sttr_award"
    CONTRACT_RECOMPETE = "contract_recompete"
    MENTOR_PROTEGE = "mentor_protege"
    JOINT_VENTURE = "joint_venture"
    TEAMING_ANNOUNCEMENT = "teaming_announcement"
    # Growth signals
    NEW_OFFICE = "new_office"
    EXECUTIVE_HIRE = "executive_hire"
    MERGER_ACQUISITION = "merger_acquisition"
    EXPANSION_ANNOUNCEMENT = "expansion_announcement"
    # Certification signals
    SAM_REGISTRATION = "sam_registration"
    CMMC_CERTIFICATION = "cmmc_certification"
    ISO_CERTIFICATION = "iso_certification"
    SOC2_CERTIFICATION = "soc2_certification"
    CMMI_CERTIFICATION = "cmmi_certification"
    CERTIFICATION_8A = "certification_8a"
    CERTIFICATION_SDVOSB = "certification_sdvosb"
    CERTIFICATION_HUBZONE = "certification_hubzone"
    CERTIFICATION_WOSB = "certification_wosb"
    CERTIFICATION_VETERAN = "certification_veteran"
    CERTIFICATION_MINORITY = "certification_minority"


class SignalSource(StrEnum):
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    ZIPRECRUITER = "ziprecruiter"
    CLEARANCEJOBS = "clearancejobs"
    SAMGOV = "samgov"
    USASPENDING = "usaspending"
    FPDS = "fpds"
    STATE_PORTAL = "state_portal"
    NEWS = "news"
    MANUAL = "manual"


class PriorityTier(StrEnum):
    A = "A"
    B = "B"
    C = "C"


# ── Company ────────────────────────────────────────────────────────────────────


class PIRCompany(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "pir_companies"
    __table_args__ = (
        UniqueConstraint("tenant_id", "domain", name="uq_pir_company_tenant_domain"),
        Index("idx_pir_company_score", "tenant_id", "overall_signal_score"),
        Index("idx_pir_company_tier", "tenant_id", "priority_tier"),
        Index("idx_pir_company_uei", "samgov_uei"),
        Index("idx_pir_company_naics", "naics_codes", postgresql_using="gin"),
    )

    # Identity
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(256), index=True)
    website: Mapped[str | None] = mapped_column(String(512))
    linkedin_url: Mapped[str | None] = mapped_column(String(512))
    samgov_uei: Mapped[str | None] = mapped_column(String(12))
    cage_code: Mapped[str | None] = mapped_column(String(10))
    duns: Mapped[str | None] = mapped_column(String(9))

    # Profile
    description: Mapped[str | None] = mapped_column(Text)
    industry: Mapped[str | None] = mapped_column(String(128))
    employee_count: Mapped[int | None] = mapped_column(Integer)
    employee_count_range: Mapped[str | None] = mapped_column(String(32))
    revenue_range: Mapped[str | None] = mapped_column(String(32))
    founded_year: Mapped[int | None] = mapped_column(Integer)
    headquarters_city: Mapped[str | None] = mapped_column(String(128))
    headquarters_state: Mapped[str | None] = mapped_column(String(64))
    headquarters_country: Mapped[str] = mapped_column(String(64), default="US")
    naics_codes: Mapped[list] = mapped_column(JSONB, default=list)
    psc_codes: Mapped[list] = mapped_column(JSONB, default=list)
    set_aside_types: Mapped[list] = mapped_column(JSONB, default=list)

    # Scores — all 0.0–100.0
    overall_signal_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    growth_momentum_score: Mapped[float] = mapped_column(Float, default=0.0)
    government_readiness_score: Mapped[float] = mapped_column(Float, default=0.0)
    priority_tier: Mapped[str] = mapped_column(String(2), default=PriorityTier.C)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_watched: Mapped[bool] = mapped_column(Boolean, default=False)
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    signals: Mapped[list["PIRSignal"]] = relationship(
        back_populates="company", cascade="all, delete-orphan", lazy="select"
    )
    ai_analyses: Mapped[list["PIRAIAnalysis"]] = relationship(
        back_populates="company", cascade="all, delete-orphan", lazy="select"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.name,
            "domain": self.domain,
            "website": self.website,
            "linkedin_url": self.linkedin_url,
            "samgov_uei": self.samgov_uei,
            "cage_code": self.cage_code,
            "industry": self.industry,
            "employee_count_range": self.employee_count_range,
            "revenue_range": self.revenue_range,
            "headquarters_city": self.headquarters_city,
            "headquarters_state": self.headquarters_state,
            "headquarters_country": self.headquarters_country,
            "naics_codes": self.naics_codes,
            "set_aside_types": self.set_aside_types,
            "overall_signal_score": self.overall_signal_score,
            "confidence_score": self.confidence_score,
            "growth_momentum_score": self.growth_momentum_score,
            "government_readiness_score": self.government_readiness_score,
            "priority_tier": self.priority_tier,
            "description": self.description,
        }


# ── Signal ─────────────────────────────────────────────────────────────────────


class PIRSignal(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "pir_signals"
    __table_args__ = (
        Index("idx_pir_signal_company_type", "company_id", "signal_type"),
        Index("idx_pir_signal_tenant_type", "tenant_id", "signal_type"),
        Index("idx_pir_signal_detected", "detected_at"),
        Index("idx_pir_signal_source", "source"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pir_companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    signal_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048))
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    raw_weight: Mapped[float] = mapped_column(Float, nullable=False)
    decay_factor: Mapped[float] = mapped_column(Float, default=1.0)
    effective_weight: Mapped[float] = mapped_column(Float, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)

    company: Mapped["PIRCompany"] = relationship(back_populates="signals")


# ── Watchlist ──────────────────────────────────────────────────────────────────


class PIRWatchlist(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "pir_watchlists"
    __table_args__ = (
        Index("idx_pir_watchlist_tenant", "tenant_id"),
        UniqueConstraint("tenant_id", "name", name="uq_pir_watchlist_name"),
    )

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    company_ids: Mapped[list] = mapped_column(JSONB, default=list)
    company_count: Mapped[int] = mapped_column(Integer, default=0)


# ── Saved Search ───────────────────────────────────────────────────────────────


class PIRSavedSearch(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "pir_saved_searches"
    __table_args__ = (Index("idx_pir_search_tenant", "tenant_id"),)

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    filters: Mapped[dict] = mapped_column(JSONB, default=dict)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    notify_on_new: Mapped[bool] = mapped_column(Boolean, default=False)


# ── AI Analysis ────────────────────────────────────────────────────────────────


class PIRAIAnalysis(Base, UUIDMixin, TimestampMixin, TenantMixin, EvidenceMixin):
    __tablename__ = "pir_ai_analyses"
    __table_args__ = (
        Index("idx_pir_analysis_company", "company_id"),
        Index("idx_pir_analysis_tenant_status", "tenant_id", "status"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pir_companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    executive_summary: Mapped[str | None] = mapped_column(Text)
    pain_points: Mapped[list] = mapped_column(JSONB, default=list)
    recommended_outreach: Mapped[str | None] = mapped_column(Text)
    buying_probability: Mapped[float | None] = mapped_column(Float)
    suggested_messaging: Mapped[list] = mapped_column(JSONB, default=list)
    potential_stakeholders: Mapped[list] = mapped_column(JSONB, default=list)
    confidence_explanation: Mapped[str | None] = mapped_column(Text)
    model_used: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)

    company: Mapped["PIRCompany"] = relationship(back_populates="ai_analyses")


# ── Scan Job ───────────────────────────────────────────────────────────────────


class PIRScanJob(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "pir_scan_jobs"
    __table_args__ = (
        Index("idx_pir_scan_tenant_status", "tenant_id", "status"),
        Index("idx_pir_scan_type", "scan_type"),
    )

    scan_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    companies_discovered: Mapped[int] = mapped_column(Integer, default=0)
    signals_detected: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    scan_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    results_summary: Mapped[dict] = mapped_column(JSONB, default=dict)
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
