"""015 — restore bid_decisions.go_no_go_threshold and .analyzed_at.

Migration 012 (schema-drift reconciliation) dropped these two columns
because cios/models/bid_decision.py never declared them, even though the
frontend's Bid/No-Bid page (components/modules/bid-decision/bid-decision-view.tsx)
depends on both — the create flow's threshold input and the "Analyzed on"
timestamp. Restoring them with the same nullable Float/timestamptz shape the
original schema (002_complete_schema.py) used.

Revision ID: 015_restore_bid_decision_columns
Revises: 014_research_report_content
Create Date: 2026-07-28
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "015_restore_bid_decision_columns"
down_revision = "014_research_report_content"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bid_decisions", sa.Column("go_no_go_threshold", sa.Float(), nullable=True))
    op.add_column(
        "bid_decisions",
        sa.Column("analyzed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bid_decisions", "analyzed_at")
    op.drop_column("bid_decisions", "go_no_go_threshold")
