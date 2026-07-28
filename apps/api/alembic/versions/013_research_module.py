"""013 — Research module: agency_profiles, agency_buying_patterns,
research_reports, and tenants.is_council_member.

First phase of the Executive Council research pipeline (Agency Intelligence
Brief only — Federal Contract Market Annual Review, Competitive Landscape
Monitor, and Procurement Intelligence Benchmark are later phases, not built
yet). The three new tables are deliberately NOT tenant-scoped — no tenant_id,
no RLS — they hold public-data-derived (SAM.gov/USASpending) market
intelligence meant to be read across every Council-member tenant, not
customer-owned data. is_council_member is a manual admin-set flag, not a
reviewed application workflow.

Revision ID: 013_research_module
Revises: 012_reconcile_schema_drift
Create Date: 2026-07-28
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "013_research_module"
down_revision = "012_reconcile_schema_drift"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("is_council_member", sa.Boolean, nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "agency_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(256), nullable=False, unique=True),
        sa.Column("usaspending_toptier_code", sa.String(16), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
            nullable=False,
        ),
    )

    # Fixed starting set (DoD, GSA, VA). toptier codes below are USASpending's
    # commonly-documented values from general reference — this environment's
    # network policy blocks api.usaspending.gov, so these could not be
    # verified against a live API call before shipping. Confirm against a
    # real USASpending response before the first live brief generation run.
    agency_profiles = sa.table(
        "agency_profiles",
        sa.column("name", sa.String),
        sa.column("usaspending_toptier_code", sa.String),
    )
    op.bulk_insert(
        agency_profiles,
        [
            {"name": "Department of Defense", "usaspending_toptier_code": "097"},
            {"name": "General Services Administration", "usaspending_toptier_code": "047"},
            {"name": "Department of Veterans Affairs", "usaspending_toptier_code": "036"},
        ],
    )

    op.create_table(
        "agency_buying_patterns",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("agency_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_obligated_amount", sa.Float, nullable=False, server_default="0"),
        sa.Column("award_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("recompete_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("top_naics_breakdown", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("source_evidence", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_agency_buying_patterns_agency_id", "agency_buying_patterns", ["agency_id"]
    )
    op.create_index(
        "idx_agency_buying_period", "agency_buying_patterns", ["agency_id", "period_start"]
    )
    op.create_unique_constraint(
        "uq_agency_period", "agency_buying_patterns", ["agency_id", "period_start", "period_end"]
    )

    op.create_table(
        "research_reports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("report_type", sa.String(64), nullable=False),
        sa.Column("period_label", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("visibility", sa.String(16), nullable=False, server_default="council_only"),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("storage_url", sa.String(512), nullable=True),
        sa.Column("generated_by_agent_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_research_report_type_period", "research_reports", ["report_type", "period_label"]
    )


def downgrade() -> None:
    op.drop_index("idx_research_report_type_period", table_name="research_reports")
    op.drop_table("research_reports")

    op.drop_constraint("uq_agency_period", "agency_buying_patterns", type_="unique")
    op.drop_index("idx_agency_buying_period", table_name="agency_buying_patterns")
    op.drop_index("ix_agency_buying_patterns_agency_id", table_name="agency_buying_patterns")
    op.drop_table("agency_buying_patterns")

    op.drop_table("agency_profiles")

    op.drop_column("tenants", "is_council_member")
