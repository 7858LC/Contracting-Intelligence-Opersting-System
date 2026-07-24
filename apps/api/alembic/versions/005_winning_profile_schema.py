"""005 — Winning Profile Hypothesis™ Engine schema (pre-award intelligence).

Revision ID: 005_winning_profile_schema
Revises: 004_pir_schema
Create Date: 2026-07-21
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "005_winning_profile_schema"
down_revision = "004_pir_schema"
branch_labels = None
depends_on = None


def _tenant_cols() -> list:
    return [
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
    ]


def _evidence_cols() -> list:
    return [
        sa.Column("evidence", postgresql.JSONB, nullable=True),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("ai_model_version", sa.String(64), nullable=True),
    ]


def _enable_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY {table}_tenant_isolation ON {table} "
        f"USING (tenant_id::text = current_setting('app.current_tenant', true))"
    )


def upgrade() -> None:
    # ── wph_solicitations ─────────────────────────────────────────────────────
    op.create_table(
        "wph_solicitations",
        *_tenant_cols(),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("solicitation_number", sa.String(128), nullable=True),
        sa.Column("agency", sa.String(256), nullable=True),
        sa.Column("sub_agency", sa.String(256), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("naics_codes", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("psc_codes", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("set_aside_type", sa.String(64), nullable=True),
        sa.Column("estimated_value", sa.Float, nullable=True),
        sa.Column("incumbent", sa.String(256), nullable=True),
        sa.Column("rule_pack", sa.String(64), nullable=False, server_default="us_federal_far"),
        sa.Column("pipeline_status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("document_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("signal_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "idx_wph_sol_tenant_status", "wph_solicitations", ["tenant_id", "pipeline_status"]
    )
    op.create_index("idx_wph_sol_number", "wph_solicitations", ["solicitation_number"])
    _enable_rls("wph_solicitations")

    # ── wph_evidence_documents ────────────────────────────────────────────────
    op.create_table(
        "wph_evidence_documents",
        *_tenant_cols(),
        sa.Column("solicitation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.String(48), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("content", sa.Text, nullable=False, server_default=""),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("source_ref", sa.String(256), nullable=True),
        sa.Column("is_extracted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("doc_metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(["solicitation_id"], ["wph_solicitations.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_wph_doc_sol", "wph_evidence_documents", ["solicitation_id"])
    op.create_index(
        "idx_wph_doc_type", "wph_evidence_documents", ["solicitation_id", "document_type"]
    )
    _enable_rls("wph_evidence_documents")

    # ── wph_signals ───────────────────────────────────────────────────────────
    op.create_table(
        "wph_signals",
        *_tenant_cols(),
        sa.Column("solicitation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category", sa.String(48), nullable=False),
        sa.Column("evidence_text", sa.Text, nullable=False),
        sa.Column("interpretation", sa.Text, nullable=True),
        sa.Column("strength", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("source_document_type", sa.String(48), nullable=True),
        sa.Column("source_ref", sa.String(256), nullable=True),
        sa.Column("keywords", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("raw", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(["solicitation_id"], ["wph_solicitations.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_wph_signal_sol", "wph_signals", ["solicitation_id"])
    op.create_index("idx_wph_signal_category", "wph_signals", ["solicitation_id", "category"])
    _enable_rls("wph_signals")

    # ── wph_profiles ──────────────────────────────────────────────────────────
    op.create_table(
        "wph_profiles",
        *_tenant_cols(),
        *_evidence_cols(),
        sa.Column("solicitation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_current", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("narrative", sa.Text, nullable=True),
        sa.Column("overall_confidence", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("evidence_strength", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("attribute_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("unknown_factors", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("status", sa.String(32), nullable=False, server_default="generated"),
        sa.Column("model_used", sa.String(64), nullable=True),
        sa.ForeignKeyConstraint(["solicitation_id"], ["wph_solicitations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("solicitation_id", "version", name="uq_wph_profile_version"),
    )
    op.create_index("idx_wph_profile_sol", "wph_profiles", ["solicitation_id"])
    op.create_index("idx_wph_profile_current", "wph_profiles", ["solicitation_id", "is_current"])
    _enable_rls("wph_profiles")

    # ── wph_profile_attributes ────────────────────────────────────────────────
    op.create_table(
        "wph_profile_attributes",
        *_tenant_cols(),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("category", sa.String(48), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("importance_weight", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("evidence_confidence", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("confidence_level", sa.String(16), nullable=False, server_default="low"),
        sa.Column("required_level", sa.Float, nullable=False, server_default="70.0"),
        sa.Column("supporting_evidence", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("evidence_source_refs", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("signal_ids", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("unknown_factors", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.ForeignKeyConstraint(["profile_id"], ["wph_profiles.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_wph_attr_profile", "wph_profile_attributes", ["profile_id"])
    op.create_index(
        "idx_wph_attr_importance", "wph_profile_attributes", ["profile_id", "importance_weight"]
    )
    _enable_rls("wph_profile_attributes")

    # ── wph_contractors ───────────────────────────────────────────────────────
    op.create_table(
        "wph_contractors",
        *_tenant_cols(),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("samgov_uei", sa.String(12), nullable=True),
        sa.Column("cage_code", sa.String(10), nullable=True),
        sa.Column("is_self", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_incumbent", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("business_size", sa.String(16), nullable=True),
        sa.Column("employee_count", sa.Integer, nullable=True),
        sa.Column("naics_codes", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("certifications", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("set_asides", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("clearances", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("capabilities", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("past_performance", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_wph_contractor_name"),
    )
    op.create_index("idx_wph_contractor_tenant", "wph_contractors", ["tenant_id"])
    _enable_rls("wph_contractors")

    # ── wph_alignments ────────────────────────────────────────────────────────
    op.create_table(
        "wph_alignments",
        *_tenant_cols(),
        *_evidence_cols(),
        sa.Column("solicitation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contractor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contractor_name", sa.String(256), nullable=False),
        sa.Column("overall_alignment_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("rank", sa.Integer, nullable=False, server_default="0"),
        sa.Column("attribute_alignments", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("gaps", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("gap_closures", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("strengths", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("weaknesses", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("model_used", sa.String(64), nullable=True),
        sa.ForeignKeyConstraint(["solicitation_id"], ["wph_solicitations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["wph_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contractor_id"], ["wph_contractors.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("profile_id", "contractor_id", name="uq_wph_align_profile_contractor"),
    )
    op.create_index("idx_wph_align_profile", "wph_alignments", ["profile_id"])
    op.create_index("idx_wph_align_rank", "wph_alignments", ["profile_id", "rank"])
    _enable_rls("wph_alignments")

    # ── wph_assessments ───────────────────────────────────────────────────────
    op.create_table(
        "wph_assessments",
        *_tenant_cols(),
        *_evidence_cols(),
        sa.Column("solicitation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_contractor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_contractor_name", sa.String(256), nullable=True),
        sa.Column("pdq_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("win_positioning_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("competitive_rank", sa.Integer, nullable=True),
        sa.Column("candidate_pool_size", sa.Integer, nullable=False, server_default="0"),
        sa.Column("recommendation", sa.String(24), nullable=False, server_default="monitor"),
        sa.Column("executive_summary", sa.Text, nullable=True),
        sa.Column("narrative", sa.Text, nullable=True),
        sa.Column("key_findings", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("decision_factors", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("critical_gaps", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("recommended_actions", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("risks", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("assumptions", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("status", sa.String(32), nullable=False, server_default="completed"),
        sa.Column("model_used", sa.String(64), nullable=True),
        sa.ForeignKeyConstraint(["solicitation_id"], ["wph_solicitations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["wph_profiles.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_wph_assess_sol", "wph_assessments", ["solicitation_id"])
    op.create_index(
        "idx_wph_assess_target", "wph_assessments", ["solicitation_id", "target_contractor_id"]
    )
    _enable_rls("wph_assessments")


def downgrade() -> None:
    for table in [
        "wph_assessments",
        "wph_alignments",
        "wph_contractors",
        "wph_profile_attributes",
        "wph_profiles",
        "wph_signals",
        "wph_evidence_documents",
        "wph_solicitations",
    ]:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.drop_table(table)
