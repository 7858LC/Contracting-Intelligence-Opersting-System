"""022 — tenants.onboarding_completed_steps / onboarding_completed_at.

/onboarding's GET /status previously hardcoded completed_steps: [] and
completion_percentage: 0 always, and POST /steps/{step} validated the step
name and returned "completed" without persisting anything — a brand new
tenant could "complete" onboarding repeatedly and the API would never
remember it happened. These two columns are what the rewritten onboarding
endpoints (see api/v1/endpoints/onboarding.py) actually read and write.

Revision ID: 022_tenant_onboarding_progress
Revises: 021_capability_gap_analysis_run
Create Date: 2026-08-01
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "022_tenant_onboarding_progress"
down_revision = "021_capability_gap_analysis_run"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "onboarding_completed_steps",
            postgresql.JSONB,
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "tenants",
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenants", "onboarding_completed_at")
    op.drop_column("tenants", "onboarding_completed_steps")
