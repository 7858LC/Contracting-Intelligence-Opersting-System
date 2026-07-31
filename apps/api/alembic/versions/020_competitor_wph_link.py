"""020 — link wph_contractors to competitors, add competitive_landscape_analyses.

WPHContractor and Competitor were two separate, unlinked concepts for "some
other company": WPHContractor exists to be *scored* (AlignmentScorer's
structured capability/certification/set-aside inputs, per solicitation),
Competitor exists to be *tracked over time* (threat_level, pricing_tendency,
a running CompetitorIntelligence log, independent of any one solicitation).
Neither should absorb the other's fields — a merge would bloat the scoring
table with dossier fields AlignmentScorer never reads, or force the intel
workflow into a per-solicitation row it doesn't conceptually belong to. What
was actually missing was a way to connect "ranked #1 in this solicitation's
WPH alignment" to "what we already know about that company," so Competitive
Intelligence's /analyze can return a front-runner + next tiers enriched with
real tracked intel instead of a bare alignment score.

wph_contractors.competitor_id is nullable (most contractors, especially
"self", have no linked Competitor) and ON DELETE SET NULL — deleting a
tracked Competitor should unlink, not cascade-delete the contractor's
alignment history.

competitive_landscape_analyses mirrors the existing pattern for computed AI
results (award_simulations, pir_ai_analyses, wph_assessments): status +
error_message so "never run" / "running" / "silently failed" are
distinguishable, JSONB for the actual front_runner/next_tiers payload.

Revision ID: 020_competitor_wph_link
Revises: 019_opportunity_analyzed_at
Create Date: 2026-07-31
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "020_competitor_wph_link"
down_revision = "019_opportunity_analyzed_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wph_contractors",
        sa.Column("competitor_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_wph_contractors_competitor_id",
        "wph_contractors",
        "competitors",
        ["competitor_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_wph_contractors_competitor_id", "wph_contractors", ["competitor_id"]
    )

    op.create_table(
        "competitive_landscape_analyses",
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
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("solicitation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("front_runner", postgresql.JSONB, nullable=True),
        sa.Column("next_tiers", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("candidate_pool_size", sa.Integer, nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence", postgresql.JSONB, nullable=True),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("ai_model_version", sa.String(64), nullable=True),
    )
    op.create_index(
        "idx_cla_tenant_opp", "competitive_landscape_analyses", ["tenant_id", "opportunity_id"]
    )
    op.create_index(
        "ix_competitive_landscape_analyses_tenant_id",
        "competitive_landscape_analyses",
        ["tenant_id"],
    )

    op.execute("ALTER TABLE competitive_landscape_analyses ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE competitive_landscape_analyses FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY competitive_landscape_analyses_tenant_isolation "
        "ON competitive_landscape_analyses "
        "USING (tenant_id::text = current_setting('app.current_tenant', true))"
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS competitive_landscape_analyses_tenant_isolation "
        "ON competitive_landscape_analyses"
    )
    op.drop_table("competitive_landscape_analyses")
    op.drop_index("ix_wph_contractors_competitor_id", table_name="wph_contractors")
    op.drop_constraint(
        "fk_wph_contractors_competitor_id", "wph_contractors", type_="foreignkey"
    )
    op.drop_column("wph_contractors", "competitor_id")
