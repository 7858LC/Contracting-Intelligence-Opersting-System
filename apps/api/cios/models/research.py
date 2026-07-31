"""Research module — platform-owned market intelligence, deliberately NOT
tenant-scoped.

Every other model in this codebase is tenant-isolated by design (RLS-forced,
TenantMixin, per-tenant vector collections). These three tables are the
one deliberate exception: they hold public-data-derived market intelligence
(aggregated from SAM.gov/USASpending, not customer inputs) meant to be read
across the platform by Executive Council members. Do not add TenantMixin to
anything in this file, and do not join these tables against tenant-scoped
data without going through the same RLS-scoping discipline documented in
core/dependencies.py — these tables carry no tenant_id at all, so there is
nothing to scope.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from cios.core.database import Base

from .base import TimestampMixin, UUIDMixin


class ReportType(StrEnum):
    AGENCY_INTELLIGENCE_BRIEF = "agency_intelligence_brief"
    # Federal Contract Market Annual Review, Competitive Landscape Monitor, and
    # Procurement Intelligence Benchmark are later phases — not implemented yet.


class ReportStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class ReportVisibility(StrEnum):
    COUNCIL_ONLY = "council_only"
    PUBLIC = "public"


class AgencyProfile(Base, UUIDMixin, TimestampMixin):
    """One tracked agency. Fixed starting set: DoD, GSA, VA."""

    __tablename__ = "agency_profiles"

    name: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    # USASpending's toptier_agency code (e.g. "097" for DoD) — the key used to
    # query its bulk award/spend endpoints.
    usaspending_toptier_code: Mapped[str] = mapped_column(String(16), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AgencyBuyingPattern(Base, UUIDMixin, TimestampMixin):
    """One agency's aggregated award activity for one period. Built from
    USASpending.gov bulk data — never derived from any tenant's own records."""

    __tablename__ = "agency_buying_patterns"
    __table_args__ = (
        UniqueConstraint("agency_id", "period_start", "period_end", name="uq_agency_period"),
        Index("idx_agency_buying_period", "agency_id", "period_start"),
    )

    agency_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    total_obligated_amount: Mapped[float] = mapped_column(Float, default=0.0)
    award_count: Mapped[int] = mapped_column(Integer, default=0)
    recompete_count: Mapped[int] = mapped_column(Integer, default=0)
    # naics_code -> obligated amount, for the "priority sectors this quarter" narrative.
    top_naics_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Raw source rows kept for audit/citation — this is what ResearchAnalystAgent
    # cites as evidence, same evidence-first requirement as every other agent.
    source_evidence: Mapped[list] = mapped_column(JSONB, default=list)


class ResearchReport(Base, UUIDMixin, TimestampMixin):
    """A generated research artifact (e.g. one quarter's Agency Intelligence
    Brief). Visibility gates who can see it; it is never tenant-scoped —
    every Council-member tenant sees the same report."""

    __tablename__ = "research_reports"
    __table_args__ = (Index("idx_research_report_type_period", "report_type", "period_label"),)

    report_type: Mapped[str] = mapped_column(String(64), nullable=False)
    period_label: Mapped[str] = mapped_column(String(32), nullable=False)  # e.g. "2026-Q3"
    status: Mapped[str] = mapped_column(String(16), default=ReportStatus.DRAFT.value)
    visibility: Mapped[str] = mapped_column(String(16), default=ReportVisibility.COUNCIL_ONLY.value)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    # Full structured report content (list of {"agency": ..., "brief": {...}}
    # sections) stored directly rather than rendered to a file and uploaded
    # to external storage — no S3/object-storage account needed for this.
    content: Mapped[list] = mapped_column(JSONB, default=list)
    storage_url: Mapped[str | None] = mapped_column(String(512))
    generated_by_agent_run_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Soft-delete only — this table has no tenant_id to scope a delete against,
    # so removal is a platform-wide action (admin.py, PlatformOperatorAuth),
    # never tenant-facing. Mirrors bid_decisions.is_archived.
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
