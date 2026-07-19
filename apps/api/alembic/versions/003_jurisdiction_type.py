"""Rename opportunities.jurisdiction → jurisdiction_type with CHECK constraint.

Revision ID: 003_jurisdiction_type
Revises: 002_complete
Create Date: 2026-07-19
"""
from alembic import op
import sqlalchemy as sa

revision = "003_jurisdiction_type"
down_revision = "002_complete"
branch_labels = None
depends_on = None

_VALID = ("federal", "state", "local", "tribal", "international")
_CHECK = "ck_opp_jurisdiction_type"


def upgrade() -> None:
    op.alter_column(
        "opportunities",
        "jurisdiction",
        new_column_name="jurisdiction_type",
        existing_type=sa.String(64),
        type_=sa.String(32),
        nullable=False,
        server_default="federal",
    )

    op.create_check_constraint(
        _CHECK,
        "opportunities",
        sa.text(f"jurisdiction_type IN {_VALID}"),
    )

    op.create_index(
        "idx_opp_jurisdiction_type",
        "opportunities",
        ["tenant_id", "jurisdiction_type"],
    )


def downgrade() -> None:
    op.drop_index("idx_opp_jurisdiction_type", table_name="opportunities")
    op.drop_constraint(_CHECK, "opportunities", type_="check")
    op.alter_column(
        "opportunities",
        "jurisdiction_type",
        new_column_name="jurisdiction",
        existing_type=sa.String(32),
        type_=sa.String(64),
        nullable=False,
        server_default="federal",
    )
