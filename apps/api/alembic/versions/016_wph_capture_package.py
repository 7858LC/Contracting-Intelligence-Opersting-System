"""016 — WPH Capture Manager Package: wph_capture_packages.

Executive-facing, human-reviewed risk-informed decision brief for one
solicitation. Deliberately not a new AI-generation pass — content is a
compile of already-computed, already-evidence-checked results (WPHProfile,
WPHAlignment rows, WPHAssessment), versioned the same way wph_profiles is
(is_current + a per-solicitation version number).

Revision ID: 016_wph_capture_package
Revises: 015_restore_bid_decision_columns
Create Date: 2026-07-28
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "016_wph_capture_package"
down_revision = "015_restore_bid_decision_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wph_capture_packages",
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
        sa.Column("solicitation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_current", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("content", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text, nullable=True),
        sa.Column("knowledge_vault_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["solicitation_id"], ["wph_solicitations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["wph_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assessment_id"], ["wph_assessments.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("solicitation_id", "version", name="uq_wph_capture_version"),
    )
    op.create_index("idx_wph_capture_sol", "wph_capture_packages", ["solicitation_id"])
    op.create_index(
        "idx_wph_capture_current", "wph_capture_packages", ["solicitation_id", "is_current"]
    )
    op.create_index(
        "ix_wph_capture_packages_tenant_id", "wph_capture_packages", ["tenant_id"]
    )
    op.create_index(
        "ix_wph_capture_packages_solicitation_id", "wph_capture_packages", ["solicitation_id"]
    )
    op.create_index(
        "ix_wph_capture_packages_profile_id", "wph_capture_packages", ["profile_id"]
    )
    op.create_index(
        "ix_wph_capture_packages_assessment_id", "wph_capture_packages", ["assessment_id"]
    )

    op.execute("ALTER TABLE wph_capture_packages ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE wph_capture_packages FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY wph_capture_packages_tenant_isolation ON wph_capture_packages "
        "USING (tenant_id::text = current_setting('app.current_tenant', true))"
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS wph_capture_packages_tenant_isolation ON wph_capture_packages"
    )
    op.drop_table("wph_capture_packages")
