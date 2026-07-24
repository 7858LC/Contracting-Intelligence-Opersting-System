"""008 — Winning Profile Hypothesis™ vehicle-contestability flag.

Adds a column to persist VehicleContestabilityFlag (see cios/wph/schemas.py),
surfaced as its own field rather than folded into the weighted attribute
average — mirrors 006_wph_shaping_risk's treatment of ShapingRiskFlag.

Revision ID: 008_wph_vehicle_contestability
Revises: 007_force_rls
Create Date: 2026-07-23
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "008_wph_vehicle_contestability"
down_revision = "007_force_rls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wph_profiles",
        sa.Column("vehicle_contestability", postgresql.JSONB, nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("wph_profiles", "vehicle_contestability")
