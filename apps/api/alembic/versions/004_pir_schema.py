"""004 — Procurement Intelligence Radar™ schema.

Revision ID: 004_pir_schema
Revises: 003_jurisdiction_type
Create Date: 2026-07-19
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "004_pir_schema"
down_revision = "003_jurisdiction_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── pir_companies ─────────────────────────────────────────────────────────
    op.create_table(
        "pir_companies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        # Identity
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("domain", sa.String(256), nullable=True),
        sa.Column("website", sa.String(512), nullable=True),
        sa.Column("linkedin_url", sa.String(512), nullable=True),
        sa.Column("samgov_uei", sa.String(12), nullable=True),
        sa.Column("cage_code", sa.String(10), nullable=True),
        sa.Column("duns", sa.String(9), nullable=True),
        # Profile
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("industry", sa.String(128), nullable=True),
        sa.Column("employee_count", sa.Integer, nullable=True),
        sa.Column("employee_count_range", sa.String(32), nullable=True),
        sa.Column("revenue_range", sa.String(32), nullable=True),
        sa.Column("founded_year", sa.Integer, nullable=True),
        sa.Column("headquarters_city", sa.String(128), nullable=True),
        sa.Column("headquarters_state", sa.String(64), nullable=True),
        sa.Column("headquarters_country", sa.String(64), nullable=False, server_default="US"),
        sa.Column("naics_codes", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("psc_codes", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("set_aside_types", postgresql.JSONB, nullable=False, server_default="[]"),
        # Scores
        sa.Column("overall_signal_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("confidence_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("growth_momentum_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("government_readiness_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("priority_tier", sa.String(2), nullable=False, server_default="C"),
        # Status
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_watched", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("last_scanned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_scored_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "domain", name="uq_pir_company_tenant_domain"),
    )
    op.create_index("idx_pir_company_score", "pir_companies", ["tenant_id", "overall_signal_score"])
    op.create_index("idx_pir_company_tier", "pir_companies", ["tenant_id", "priority_tier"])
    op.create_index("idx_pir_company_uei", "pir_companies", ["samgov_uei"])
    op.create_index("idx_pir_company_domain", "pir_companies", ["domain"])
    op.create_index(
        "idx_pir_company_naics",
        "pir_companies",
        ["naics_codes"],
        postgresql_using="gin",
    )

    # RLS
    op.execute("ALTER TABLE pir_companies ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY pir_companies_tenant_isolation ON pir_companies
            USING (tenant_id::text = current_setting('app.current_tenant', true))
    """)

    # ── pir_signals ───────────────────────────────────────────────────────────
    op.create_table(
        "pir_signals",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_type", sa.String(64), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("raw_weight", sa.Float, nullable=False),
        sa.Column("decay_factor", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("effective_weight", sa.Float, nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_data", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("is_verified", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_duplicate", sa.Boolean, nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["company_id"], ["pir_companies.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_pir_signal_company_type", "pir_signals", ["company_id", "signal_type"])
    op.create_index("idx_pir_signal_tenant_type", "pir_signals", ["tenant_id", "signal_type"])
    op.create_index("idx_pir_signal_detected", "pir_signals", ["detected_at"])
    op.create_index("idx_pir_signal_source", "pir_signals", ["source"])
    op.execute("ALTER TABLE pir_signals ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY pir_signals_tenant_isolation ON pir_signals
            USING (tenant_id::text = current_setting('app.current_tenant', true))
    """)

    # ── pir_watchlists ────────────────────────────────────────────────────────
    op.create_table(
        "pir_watchlists",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("company_ids", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("company_count", sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_pir_watchlist_name"),
    )
    op.create_index("idx_pir_watchlist_tenant", "pir_watchlists", ["tenant_id"])
    op.execute("ALTER TABLE pir_watchlists ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY pir_watchlists_tenant_isolation ON pir_watchlists
            USING (tenant_id::text = current_setting('app.current_tenant', true))
    """)

    # ── pir_saved_searches ────────────────────────────────────────────────────
    op.create_table(
        "pir_saved_searches",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filters", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("notify_on_new", sa.Boolean, nullable=False, server_default="false"),
    )
    op.create_index("idx_pir_search_tenant", "pir_saved_searches", ["tenant_id"])
    op.execute("ALTER TABLE pir_saved_searches ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY pir_saved_searches_tenant_isolation ON pir_saved_searches
            USING (tenant_id::text = current_setting('app.current_tenant', true))
    """)

    # ── pir_ai_analyses ───────────────────────────────────────────────────────
    op.create_table(
        "pir_ai_analyses",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        # EvidenceMixin fields
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("evidence", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("rule_citations", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("assumptions", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("risks", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("alternatives", postgresql.JSONB, nullable=False, server_default="[]"),
        # Analysis fields
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("executive_summary", sa.Text, nullable=True),
        sa.Column("pain_points", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("recommended_outreach", sa.Text, nullable=True),
        sa.Column("buying_probability", sa.Float, nullable=True),
        sa.Column("suggested_messaging", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("potential_stakeholders", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("confidence_explanation", sa.Text, nullable=True),
        sa.Column("model_used", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["pir_companies.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_pir_analysis_company", "pir_ai_analyses", ["company_id"])
    op.create_index("idx_pir_analysis_tenant_status", "pir_ai_analyses", ["tenant_id", "status"])
    op.execute("ALTER TABLE pir_ai_analyses ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY pir_ai_analyses_tenant_isolation ON pir_ai_analyses
            USING (tenant_id::text = current_setting('app.current_tenant', true))
    """)

    # ── pir_scan_jobs ─────────────────────────────────────────────────────────
    op.create_table(
        "pir_scan_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.Column("scan_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("companies_discovered", sa.Integer, nullable=False, server_default="0"),
        sa.Column("signals_detected", sa.Integer, nullable=False, server_default="0"),
        sa.Column("errors", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("scan_config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("results_summary", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("triggered_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("idx_pir_scan_tenant_status", "pir_scan_jobs", ["tenant_id", "status"])
    op.create_index("idx_pir_scan_type", "pir_scan_jobs", ["scan_type"])
    op.execute("ALTER TABLE pir_scan_jobs ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY pir_scan_jobs_tenant_isolation ON pir_scan_jobs
            USING (tenant_id::text = current_setting('app.current_tenant', true))
    """)

    # ── Celery Beat schedule ───────────────────────────────────────────────────
    # Note: Beat schedule added in tasks/__init__.py, not here.


def downgrade() -> None:
    for table in [
        "pir_scan_jobs",
        "pir_ai_analyses",
        "pir_saved_searches",
        "pir_watchlists",
        "pir_signals",
        "pir_companies",
    ]:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.drop_table(table)
