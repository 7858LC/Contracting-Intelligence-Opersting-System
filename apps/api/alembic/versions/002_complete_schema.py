"""Complete CIOS schema — remaining tables.

Revision ID: 002_complete
Revises: 001_initial
Create Date: 2026-07-18
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "002_complete"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Tenant Invites ────────────────────────────────────────────────────────
    op.create_table(
        "tenant_invites",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(256), nullable=False),
        sa.Column("role", sa.String(32), default="member"),
        sa.Column("token", sa.String(64), unique=True, nullable=False),
        sa.Column("invited_by", UUID(as_uuid=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # ── API Keys ──────────────────────────────────────────────────────────────
    op.create_table(
        "api_keys",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("key_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("key_prefix", sa.String(16), nullable=False),
        sa.Column("scopes", JSONB(), default=[]),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # ── Bid Decisions ─────────────────────────────────────────────────────────
    op.create_table(
        "bid_decisions",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_title", sa.String(512)),
        sa.Column("decision", sa.String(32)),
        sa.Column("human_decision", sa.String(32)),
        sa.Column("human_rationale", sa.Text()),
        sa.Column("overall_score", sa.Float()),
        sa.Column("strategic_fit_score", sa.Float()),
        sa.Column("win_probability_score", sa.Float()),
        sa.Column("past_performance_score", sa.Float()),
        sa.Column("capability_score", sa.Float()),
        sa.Column("competitive_position_score", sa.Float()),
        sa.Column("cost_of_bid_score", sa.Float()),
        sa.Column("risk_score", sa.Float()),
        sa.Column("relationship_score", sa.Float()),
        sa.Column("go_no_go_threshold", sa.Float(), default=65),
        sa.Column("scoring_weights", JSONB(), default={}),
        sa.Column("rationale", sa.Text()),
        sa.Column("risk_factors", JSONB(), default=[]),
        sa.Column("evidence", JSONB()),
        sa.Column("confidence_score", sa.Float()),
        sa.Column("ai_model_version", sa.String(64)),
        sa.Column("analyzed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_bd_tenant_opp", "bid_decisions", ["tenant_id", "opportunity_id"])
    op.execute("ALTER TABLE bid_decisions ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON bid_decisions
        USING (tenant_id::text = current_setting('app.current_tenant', true));
    """)

    # ── Capabilities ──────────────────────────────────────────────────────────
    op.create_table(
        "capabilities",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("proficiency_level", sa.Integer()),
        sa.Column("proficiency_score", sa.Float()),
        sa.Column("maturity_level", sa.String(32)),
        sa.Column("is_certified", sa.Boolean(), default=False),
        sa.Column("certifications", JSONB(), default=[]),
        sa.Column("gap_score", sa.Float()),
        sa.Column("gap_analysis", JSONB()),
        sa.Column("improvement_plan", sa.Text()),
        sa.Column("supporting_evidence", JSONB(), default=[]),
        sa.Column("naics_codes", JSONB(), default=[]),
        sa.Column("psc_codes", JSONB(), default=[]),
        sa.Column("tools_and_technologies", JSONB(), default=[]),
        sa.Column("team_members_count", sa.Integer()),
        sa.Column("last_demonstrated", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_cap_tenant_category", "capabilities", ["tenant_id", "category"])
    op.execute("ALTER TABLE capabilities ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON capabilities
        USING (tenant_id::text = current_setting('app.current_tenant', true));
    """)

    # ── Capability Gaps ───────────────────────────────────────────────────────
    op.create_table(
        "capability_gaps",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", sa.String(64)),
        sa.Column("gap_name", sa.String(256), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), default="medium"),
        sa.Column("description", sa.Text()),
        sa.Column("remediation_options", JSONB(), default=[]),
        sa.Column("estimated_cost_to_close", sa.Float()),
        sa.Column("estimated_time_to_close_days", sa.Integer()),
        sa.Column("teaming_recommendation", sa.Text()),
        sa.Column("status", sa.String(32), default="open"),
        sa.Column("evidence", JSONB()),
        sa.Column("confidence_score", sa.Float()),
        sa.Column("ai_model_version", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.execute("ALTER TABLE capability_gaps ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON capability_gaps
        USING (tenant_id::text = current_setting('app.current_tenant', true));
    """)

    # ── Past Performances ─────────────────────────────────────────────────────
    op.create_table(
        "past_performances",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("contract_number", sa.String(64)),
        sa.Column("contract_title", sa.String(512), nullable=False),
        sa.Column("agency", sa.String(256)),
        sa.Column("contract_value", sa.Float()),
        sa.Column("period_of_performance_start", sa.Date()),
        sa.Column("period_of_performance_end", sa.Date()),
        sa.Column("naics_code", sa.String(16)),
        sa.Column("place_of_performance", sa.String(256)),
        sa.Column("description", sa.Text()),
        sa.Column("key_personnel", JSONB(), default=[]),
        sa.Column("subcontractors", JSONB(), default=[]),
        sa.Column("cpars_rating", sa.String(32)),
        sa.Column("ppirs_rating", sa.String(32)),
        sa.Column("relevance_score", sa.Float()),
        sa.Column("tags", JSONB(), default=[]),
        sa.Column("is_confidential", sa.Boolean(), default=False),
        sa.Column("evidence", JSONB()),
        sa.Column("confidence_score", sa.Float()),
        sa.Column("ai_model_version", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_pp_tenant", "past_performances", ["tenant_id"])
    op.execute("ALTER TABLE past_performances ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON past_performances
        USING (tenant_id::text = current_setting('app.current_tenant', true));
    """)

    # ── Teaming Recommendations ───────────────────────────────────────────────
    op.create_table(
        "teaming_recommendations",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("prime_or_sub", sa.String(16), default="prime"),
        sa.Column("rationale", sa.Text()),
        sa.Column("team_structure", JSONB(), default={}),
        sa.Column("capability_gaps_addressed", JSONB(), default=[]),
        sa.Column("recommended_partners", JSONB(), default=[]),
        sa.Column("risk_assessment", JSONB()),
        sa.Column("win_probability_impact", sa.Float()),
        sa.Column("risks", JSONB(), default=[]),
        sa.Column("status", sa.String(32), default="draft"),
        sa.Column("evidence", JSONB()),
        sa.Column("confidence_score", sa.Float()),
        sa.Column("ai_model_version", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.execute("ALTER TABLE teaming_recommendations ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON teaming_recommendations
        USING (tenant_id::text = current_setting('app.current_tenant', true));
    """)

    # ── Teaming Partners ──────────────────────────────────────────────────────
    op.create_table(
        "teaming_partners",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("company_name", sa.String(256), nullable=False),
        sa.Column("cage_code", sa.String(8)),
        sa.Column("duns_number", sa.String(13)),
        sa.Column("sam_unique_id", sa.String(64)),
        sa.Column("website", sa.String(512)),
        sa.Column("naics_codes", JSONB(), default=[]),
        sa.Column("psc_codes", JSONB(), default=[]),
        sa.Column("capabilities", JSONB(), default=[]),
        sa.Column("socioeconomic_status", JSONB(), default=[]),
        sa.Column("past_performance_rating", sa.Integer()),
        sa.Column("active_agreements", sa.Boolean(), default=False),
        sa.Column("relationship_strength", sa.Integer(), default=3),
        sa.Column("poc_name", sa.String(256)),
        sa.Column("poc_email", sa.String(256)),
        sa.Column("notes", sa.Text()),
        sa.Column("ai_compatibility_score", sa.Float()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_tp_tenant", "teaming_partners", ["tenant_id"])
    op.execute("ALTER TABLE teaming_partners ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON teaming_partners
        USING (tenant_id::text = current_setting('app.current_tenant', true));
    """)

    # ── Competitors ───────────────────────────────────────────────────────────
    op.create_table(
        "competitors",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("company_name", sa.String(256), nullable=False),
        sa.Column("cage_code", sa.String(8)),
        sa.Column("duns_number", sa.String(13)),
        sa.Column("naics_codes", JSONB(), default=[]),
        sa.Column("capabilities_summary", sa.Text()),
        sa.Column("known_strengths", JSONB(), default=[]),
        sa.Column("known_weaknesses", JSONB(), default=[]),
        sa.Column("win_rate_estimate", sa.Float()),
        sa.Column("annual_contract_volume", sa.Float()),
        sa.Column("past_awards", JSONB(), default=[]),
        sa.Column("agency_relationships", JSONB(), default=[]),
        sa.Column("pricing_tendency", sa.String(32)),
        sa.Column("threat_level", sa.String(16), default="medium"),
        sa.Column("socioeconomic_statuses", JSONB(), default=[]),
        sa.Column("active_clearances", JSONB(), default=[]),
        sa.Column("certifications", JSONB(), default=[]),
        sa.Column("notes", sa.Text()),
        sa.Column("tags", JSONB(), default=[]),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_comp_tenant", "competitors", ["tenant_id"])
    op.execute("ALTER TABLE competitors ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON competitors
        USING (tenant_id::text = current_setting('app.current_tenant', true));
    """)

    # ── Competitor Intelligence ───────────────────────────────────────────────
    op.create_table(
        "competitor_intelligence",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("competitor_id", UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", UUID(as_uuid=True)),
        sa.Column("intel_type", sa.String(64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(256)),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("relevance_score", sa.Float()),
        sa.Column("is_verified", sa.Boolean()),
        sa.Column("evidence", JSONB()),
        sa.Column("confidence_score", sa.Float()),
        sa.Column("ai_model_version", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.execute("ALTER TABLE competitor_intelligence ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON competitor_intelligence
        USING (tenant_id::text = current_setting('app.current_tenant', true));
    """)

    # ── Knowledge Chunks ──────────────────────────────────────────────────────
    op.create_table(
        "knowledge_chunks",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("qdrant_point_id", sa.String(64)),
        sa.Column("token_count", sa.Integer()),
        sa.Column("extra_metadata", JSONB(), default={}),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_kc_document", "knowledge_chunks", ["document_id"])
    op.execute("ALTER TABLE knowledge_chunks ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON knowledge_chunks
        USING (tenant_id::text = current_setting('app.current_tenant', true));
    """)

    # ── Agent Runs ────────────────────────────────────────────────────────────
    op.create_table(
        "agent_runs",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("agent_type", sa.String(64), nullable=False),
        sa.Column("agent_name", sa.String(128), nullable=False),
        sa.Column("resource_type", sa.String(64)),
        sa.Column("resource_id", UUID(as_uuid=True)),
        sa.Column("status", sa.String(32), default="pending"),
        sa.Column("model_used", sa.String(64)),
        sa.Column("prompt_tokens", sa.Integer()),
        sa.Column("completion_tokens", sa.Integer()),
        sa.Column("total_cost_usd", sa.Float()),
        sa.Column("input_snapshot", JSONB()),
        sa.Column("output", JSONB()),
        sa.Column("rule_pack", sa.String(64)),
        sa.Column("rule_citations", JSONB(), default=[]),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index(
        "idx_ar_tenant_resource", "agent_runs", ["tenant_id", "resource_type", "resource_id"]
    )
    op.execute("ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON agent_runs
        USING (tenant_id::text = current_setting('app.current_tenant', true));
    """)

    # ── Agent Run Steps ───────────────────────────────────────────────────────
    op.create_table(
        "agent_run_steps",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "agent_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("agent_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("step_name", sa.String(128)),
        sa.Column("agent_name", sa.String(128)),
        sa.Column("model_used", sa.String(64)),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("reasoning", sa.Text()),
        sa.Column("output", JSONB()),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_ars_run", "agent_run_steps", ["agent_run_id"])
    op.execute("ALTER TABLE agent_run_steps ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON agent_run_steps
        USING (tenant_id::text = current_setting('app.current_tenant', true));
    """)

    # ── Invoices ──────────────────────────────────────────────────────────────
    op.create_table(
        "invoices",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("stripe_invoice_id", sa.String(128), unique=True),
        sa.Column("amount_due", sa.Integer(), nullable=False),
        sa.Column("amount_paid", sa.Integer()),
        sa.Column("currency", sa.String(8), default="usd"),
        sa.Column("status", sa.String(32)),
        sa.Column("invoice_pdf", sa.String(2048)),
        sa.Column("period_start", sa.DateTime(timezone=True)),
        sa.Column("period_end", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_inv_tenant", "invoices", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("invoices")
    op.drop_table("agent_run_steps")
    op.drop_table("agent_runs")
    op.drop_table("knowledge_chunks")
    op.drop_table("competitor_intelligence")
    op.drop_table("competitors")
    op.drop_table("teaming_partners")
    op.drop_table("teaming_recommendations")
    op.drop_table("past_performances")
    op.drop_table("capability_gaps")
    op.drop_table("capabilities")
    op.drop_table("bid_decisions")
    op.drop_table("api_keys")
    op.drop_table("tenant_invites")
