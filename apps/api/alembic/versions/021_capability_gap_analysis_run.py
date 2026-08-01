"""021 — capability_gap_analysis_runs + CapabilityGap.analysis_run_id.

Module 5/15's /capabilities/analyze-gaps previously queued a Celery task
that did nothing (tasks/gap_analysis.py returned a hardcoded
{"status": "completed"} without touching the database) — the capability
gap analysis pipeline never actually ran. Wiring it for real means turning
the WPH engine's already-computed, per-attribute gap/gap-closure output
(WPHAlignment.gaps + .gap_closures for the tenant's is_self contractor,
see wph/alignment.py's AlignmentScorer/GapCloser) into persisted
CapabilityGap rows.

capability_gap_analysis_runs mirrors the same tracking pattern as
competitive_landscape_analyses (migration 020) / award_simulations:
status + error_message so "never run" / "running" / "silently failed" /
"completed" are distinguishable to the frontend poller, since an empty
CapabilityGap list is otherwise ambiguous (no WPH profile yet vs.
genuinely zero gaps).

capability_gaps.analysis_run_id links each gap row to the run that
produced it, nullable + ON DELETE CASCADE so deleting a run cleans up its
gaps without constraining any gap created some other way in the future.

Revision ID: 021_capability_gap_analysis_run
Revises: 020_competitor_wph_link
Create Date: 2026-08-01
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "021_capability_gap_analysis_run"
down_revision = "020_competitor_wph_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "capability_gap_analysis_runs",
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
        sa.Column("gap_count", sa.Integer, nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_cgar_tenant_opp", "capability_gap_analysis_runs", ["tenant_id", "opportunity_id"]
    )
    op.create_index(
        "ix_capability_gap_analysis_runs_tenant_id",
        "capability_gap_analysis_runs",
        ["tenant_id"],
    )

    op.execute("ALTER TABLE capability_gap_analysis_runs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE capability_gap_analysis_runs FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY capability_gap_analysis_runs_tenant_isolation "
        "ON capability_gap_analysis_runs "
        "USING (tenant_id::text = current_setting('app.current_tenant', true))"
    )

    op.add_column(
        "capability_gaps",
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_capability_gaps_analysis_run_id",
        "capability_gaps",
        "capability_gap_analysis_runs",
        ["analysis_run_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_capability_gaps_analysis_run_id", "capability_gaps", ["analysis_run_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_capability_gaps_analysis_run_id", table_name="capability_gaps")
    op.drop_constraint(
        "fk_capability_gaps_analysis_run_id", "capability_gaps", type_="foreignkey"
    )
    op.drop_column("capability_gaps", "analysis_run_id")

    op.execute(
        "DROP POLICY IF EXISTS capability_gap_analysis_runs_tenant_isolation "
        "ON capability_gap_analysis_runs"
    )
    op.drop_table("capability_gap_analysis_runs")
