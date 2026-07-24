"""006 — Winning Profile Hypothesis™ shaping-risk flag.

Adds a column to persist ShapingRiskFlag (see cios/wph/schemas.py), surfaced as
its own field rather than folded into the weighted attribute average.

Revision ID: 006_wph_shaping_risk
Revises: 005_winning_profile_schema
Create Date: 2026-07-21
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "006_wph_shaping_risk"
down_revision = "005_winning_profile_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wph_profiles",
        sa.Column("shaping_risk", postgresql.JSONB, nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("wph_profiles", "shaping_risk")
