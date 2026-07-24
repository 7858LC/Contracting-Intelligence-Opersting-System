"""011 — WPH task-order fair-opportunity flag + task-order solicitation context.

Layer (b) of IDIQ contestability, sketched at freeze item #3 alongside
008_wph_vehicle_contestability's layer (a): once a firm holds (or is
evaluating) a seat on a base vehicle, individual task orders under it are
either openly competed among awardees via fair opportunity (FAR 16.505(b))
or directed/sole-sourced under a fair-opportunity exception (logical
follow-on, urgency, only-one-capable, etc.) — a different question from
whether the base vehicle itself admits new entrants.

Adds:
- wph_solicitations: is_task_order / base_vehicle_name /
  base_vehicle_contract_number, so a task-order evidence package can note
  which vehicle it's under without requiring that vehicle to itself be
  modeled as a WPHSolicitation row.
- wph_profiles.task_order_fair_opportunity: mirrors
  008's vehicle_contestability column — same "separate flag, never folded
  into the weighted attribute average" treatment as shaping_risk and
  vehicle_contestability.

Revision ID: 011_wph_task_order_fair_opp
Revises: 010_platform_admin
Create Date: 2026-07-24
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "011_wph_task_order_fair_opp"
down_revision = "010_platform_admin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wph_solicitations",
        sa.Column("is_task_order", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.add_column("wph_solicitations", sa.Column("base_vehicle_name", sa.String(256)))
    op.add_column("wph_solicitations", sa.Column("base_vehicle_contract_number", sa.String(128)))
    op.add_column(
        "wph_profiles",
        sa.Column(
            "task_order_fair_opportunity", postgresql.JSONB, nullable=False, server_default="{}"
        ),
    )


def downgrade() -> None:
    op.drop_column("wph_profiles", "task_order_fair_opportunity")
    op.drop_column("wph_solicitations", "base_vehicle_contract_number")
    op.drop_column("wph_solicitations", "base_vehicle_name")
    op.drop_column("wph_solicitations", "is_task_order")
