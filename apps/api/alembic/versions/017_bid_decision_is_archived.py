"""017 — add bid_decisions.is_archived.

Soft-delete flag for the new DELETE /bid-decisions/{id} endpoint, mirroring
opportunities.is_archived — a mistaken or accidental delete stays
recoverable directly from the database rather than depending on a Postgres
backup/restore. NOT NULL with a server-side default since the table may
already have rows.

Revision ID: 017_bid_decision_is_archived
Revises: 016_wph_capture_package
Create Date: 2026-07-30
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "017_bid_decision_is_archived"
down_revision = "016_wph_capture_package"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bid_decisions",
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("bid_decisions", "is_archived")
