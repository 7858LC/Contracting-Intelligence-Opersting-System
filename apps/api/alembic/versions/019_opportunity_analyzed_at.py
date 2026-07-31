"""019 — add opportunities.analyzed_at.

Set only on a completed run_opportunity_analysis task, mirroring
bid_decisions.analyzed_at (015/017) — without it, "analysis never
triggered" and "analysis ran but every score came back null" are both
just award_probability_score IS NULL, and the frontend has no way to
distinguish "never analyzed" from "analysis pending" from "analysis
silently failed" (they render identically). Nullable, no server default —
existing rows have no analysis run to record a timestamp for.

Revision ID: 019_opportunity_analyzed_at
Revises: 018_research_report_is_archived
Create Date: 2026-07-31
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "019_opportunity_analyzed_at"
down_revision = "018_research_report_is_archived"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "opportunities",
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("opportunities", "analyzed_at")
