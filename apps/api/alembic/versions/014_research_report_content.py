"""014 — research_reports.content: store report content directly in the DB
instead of uploading a rendered file to S3.

No AWS/S3 account was actually available at the time Phase 1 shipped;
storing the structured brief sections (JSONB) directly is simpler and
sufficient at this scale (a handful of small quarterly reports).
storage_url is left in place, nullable and unused, rather than dropped in
the same pass — nothing currently reads or writes it.

Revision ID: 014_research_report_content
Revises: 013_research_module
Create Date: 2026-07-28
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "014_research_report_content"
down_revision = "013_research_module"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "research_reports",
        sa.Column("content", postgresql.JSONB, nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("research_reports", "content")
