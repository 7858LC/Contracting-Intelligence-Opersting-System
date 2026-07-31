"""018 — add research_reports.is_archived.

Soft-delete flag for the new admin-only DELETE /admin/research/reports/{id}
endpoint. ResearchReport carries no tenant_id (see cios/models/research.py's
module docstring — deliberately platform-owned, shared across every
Council-member tenant), so removing one is a landlord action, not a
tenant-facing one, mirroring bid_decisions.is_archived (017) for the same
"stays recoverable directly from the database" reasoning. NOT NULL with a
server-side default since the table may already have rows.

Revision ID: 018_research_report_is_archived
Revises: 017_bid_decision_is_archived
Create Date: 2026-07-31
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "018_research_report_is_archived"
down_revision = "017_bid_decision_is_archived"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "research_reports",
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("research_reports", "is_archived")
