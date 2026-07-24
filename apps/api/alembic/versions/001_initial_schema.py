"""Initial CIOS database schema.

Revision ID: 001_initial
Revises:
Create Date: 2026-07-18
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID

from alembic import op

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    # ── Tenants ──────────────────────────────────────────────────────────────
    op.create_table(
        "tenants",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False, unique=True),
        sa.Column("plan", sa.String(32), default="starter"),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("settings", JSONB(), default={}),
        sa.Column("naics_codes", JSONB(), default=[]),
        sa.Column("cage_code", sa.String(8)),
        sa.Column("duns_number", sa.String(13)),
        sa.Column("sam_unique_id", sa.String(64)),
        sa.Column("small_business_designations", JSONB(), default=[]),
        sa.Column("annual_revenue_band", sa.String(32)),
        sa.Column("employee_count_band", sa.String(32)),
        sa.Column("primary_jurisdictions", JSONB(), default=[]),
        sa.Column("encryption_key_reference", sa.String(256)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_tenants_slug", "tenants", ["slug"])

    # ── Tenant Members ────────────────────────────────────────────────────────
    op.create_table(
        "tenant_members",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(256), nullable=False),
        sa.Column("full_name", sa.String(256)),
        sa.Column("role", sa.String(32), default="member"),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_tm_user_id", "tenant_members", ["user_id"])
    op.create_unique_constraint("uq_tenant_member", "tenant_members", ["tenant_id", "user_id"])

    # ── Audit Logs ────────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", UUID(as_uuid=True)),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64)),
        sa.Column("changes", JSONB()),
        sa.Column("extra_metadata", JSONB()),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.String(512)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("idx_audit_tenant_created", "audit_logs", ["tenant_id", "created_at"])

    # ── Opportunities ─────────────────────────────────────────────────────────
    op.create_table(
        "opportunities",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(128)),
        sa.Column("source", sa.String(64), nullable=False, default="manual"),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("solicitation_number", sa.String(128)),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("agency", sa.String(256)),
        sa.Column("sub_agency", sa.String(256)),
        sa.Column("office", sa.String(256)),
        sa.Column("jurisdiction", sa.String(64), default="federal"),
        sa.Column("naics_codes", JSONB(), default=[]),
        sa.Column("psc_codes", JSONB(), default=[]),
        sa.Column("set_aside_type", sa.String(64)),
        sa.Column("solicitation_type", sa.String(64)),
        sa.Column("contract_type", sa.String(64)),
        sa.Column("estimated_value_min", sa.Float()),
        sa.Column("estimated_value_max", sa.Float()),
        sa.Column("ceiling_value", sa.Float()),
        sa.Column("currency", sa.String(3), default="USD"),
        sa.Column("posted_at", sa.DateTime(timezone=True)),
        sa.Column("response_deadline", sa.DateTime(timezone=True)),
        sa.Column("award_date", sa.DateTime(timezone=True)),
        sa.Column("period_of_performance_start", sa.DateTime(timezone=True)),
        sa.Column("period_of_performance_end", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(32), default="active"),
        sa.Column("pipeline_stage", sa.String(32), default="identified"),
        sa.Column("award_probability_score", sa.Float()),
        sa.Column("bid_no_bid_recommendation", sa.String(16)),
        sa.Column("proposal_readiness_score", sa.Float()),
        sa.Column("competitive_intensity", sa.String(16)),
        sa.Column("evaluation_criteria", JSONB(), default=[]),
        sa.Column("key_requirements", JSONB(), default=[]),
        sa.Column("incumbent", sa.String(256)),
        sa.Column("anticipated_competitors", JSONB(), default=[]),
        sa.Column("procurement_rule_pack", sa.String(64), default="us_federal_far"),
        sa.Column("search_vector", TSVECTOR()),
        sa.Column("raw_document_key", sa.String(512)),
        sa.Column("attachments", JSONB(), default=[]),
        sa.Column("is_archived", sa.Boolean(), default=False),
        sa.Column("evidence", JSONB()),
        sa.Column("confidence_score", sa.Float()),
        sa.Column("ai_model_version", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_opp_tenant_status", "opportunities", ["tenant_id", "status"])
    op.create_index("idx_opp_response_deadline", "opportunities", ["response_deadline"])
    op.create_index("idx_opp_award_probability", "opportunities", ["award_probability_score"])
    op.create_index("idx_opp_search", "opportunities", ["search_vector"], postgresql_using="gin")

    # Full-text search trigger
    # asyncpg's extended query protocol rejects multiple commands in one
    # execute() call, so the function and trigger must be separate statements.
    op.execute("""
        CREATE OR REPLACE FUNCTION update_opportunity_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english',
                COALESCE(NEW.title, '') || ' ' ||
                COALESCE(NEW.agency, '') || ' ' ||
                COALESCE(NEW.solicitation_number, '') || ' ' ||
                COALESCE(NEW.description, '')
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER opportunity_search_vector_update
        BEFORE INSERT OR UPDATE ON opportunities
        FOR EACH ROW EXECUTE FUNCTION update_opportunity_search_vector();
    """)

    # Row Level Security
    op.execute("ALTER TABLE opportunities ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON opportunities
        USING (tenant_id::text = current_setting('app.current_tenant', true));
    """)

    # ── Award Simulations ─────────────────────────────────────────────────────
    op.create_table(
        "award_simulations",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("status", sa.String(32), default="pending"),
        sa.Column("simulation_type", sa.String(64), default="full_source_selection"),
        sa.Column("evaluation_methodology", sa.String(64), default="BEST_VALUE_TRADEOFF"),
        sa.Column("evaluation_factors", JSONB(), default=[]),
        sa.Column("technical_score", sa.Float()),
        sa.Column("management_score", sa.Float()),
        sa.Column("past_performance_score", sa.Float()),
        sa.Column("price_competitiveness_score", sa.Float()),
        sa.Column("small_business_score", sa.Float()),
        sa.Column("compliance_score", sa.Float()),
        sa.Column("risk_score", sa.Float()),
        sa.Column("overall_score", sa.Float()),
        sa.Column("award_probability", sa.Float()),
        sa.Column("significant_weaknesses", JSONB(), default=[]),
        sa.Column("deficiencies", JSONB(), default=[]),
        sa.Column("strengths", JSONB(), default=[]),
        sa.Column("risks", JSONB(), default=[]),
        sa.Column("red_team_comments", JSONB(), default=[]),
        sa.Column("suggested_improvements", JSONB(), default=[]),
        sa.Column("executive_summary", sa.Text()),
        sa.Column("gate_review_recommendation", sa.String(16)),
        sa.Column("competitor_analysis", JSONB(), default=[]),
        sa.Column("price_to_win_estimate", sa.Float()),
        sa.Column("rule_pack", sa.String(64), default="us_federal_far"),
        sa.Column("rule_citations", JSONB(), default=[]),
        sa.Column("evidence", JSONB()),
        sa.Column("confidence_score", sa.Float()),
        sa.Column("ai_model_version", sa.String(64)),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_sim_tenant_opp", "award_simulations", ["tenant_id", "opportunity_id"])

    op.execute("ALTER TABLE award_simulations ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON award_simulations
        USING (tenant_id::text = current_setting('app.current_tenant', true));
    """)

    # ── Knowledge Documents ───────────────────────────────────────────────────
    op.create_table(
        "knowledge_documents",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("document_type", sa.String(64), nullable=False),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("s3_key", sa.String(512)),
        sa.Column("file_name", sa.String(256)),
        sa.Column("file_size_bytes", sa.Integer()),
        sa.Column("mime_type", sa.String(128)),
        sa.Column("page_count", sa.Integer()),
        sa.Column("description", sa.Text()),
        sa.Column("extracted_text", sa.Text()),
        sa.Column("extra_metadata", JSONB(), default={}),
        sa.Column("vectorization_status", sa.String(32), default="pending"),
        sa.Column("is_vectorized", sa.Boolean(), default=False),
        sa.Column("chunk_count", sa.Integer(), default=0),
        sa.Column("vectorized_at", sa.DateTime(timezone=True)),
        sa.Column("qdrant_collection", sa.String(128)),
        sa.Column("related_opportunity_id", UUID(as_uuid=True)),
        sa.Column("tags", JSONB(), default=[]),
        sa.Column("uploaded_by", UUID(as_uuid=True), nullable=False),
        sa.Column("is_confidential", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_kd_tenant_type", "knowledge_documents", ["tenant_id", "document_type"])

    op.execute("ALTER TABLE knowledge_documents ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON knowledge_documents
        USING (tenant_id::text = current_setting('app.current_tenant', true));
    """)

    # ── Subscriptions ─────────────────────────────────────────────────────────
    op.create_table(
        "subscriptions",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("plan", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), default="active"),
        sa.Column("stripe_customer_id", sa.String(128), unique=True),
        sa.Column("stripe_subscription_id", sa.String(128), unique=True),
        sa.Column("stripe_price_id", sa.String(128)),
        sa.Column("current_period_start", sa.DateTime(timezone=True)),
        sa.Column("current_period_end", sa.DateTime(timezone=True)),
        sa.Column("trial_end", sa.DateTime(timezone=True)),
        sa.Column("cancel_at_period_end", sa.Boolean()),
        sa.Column("seats", sa.Integer(), default=1),
        sa.Column("features", JSONB(), default={}),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_sub_tenant", "subscriptions", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("subscriptions")
    op.drop_table("knowledge_documents")
    op.drop_table("award_simulations")
    op.drop_table("opportunities")
    op.drop_table("audit_logs")
    op.drop_table("tenant_members")
    op.drop_table("tenants")
