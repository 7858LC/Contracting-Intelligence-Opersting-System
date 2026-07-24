"""010 — Landlord/tenant-ops layer: platform_admins table.

Replaces the static "admin key = sha256(JWT_SECRET)" scheme (a deterministic
function of the same secret tenant JWTs depend on, not an independent,
rotatable, or per-person credential) with real per-person landlord accounts.
Deliberately not tenant-scoped — no tenant_id, no RLS — this is the operator
identity space, separate from every tenant's.

Revision ID: 010_platform_admin
Revises: 009_tenant_login_password
Create Date: 2026-07-24
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "010_platform_admin"
down_revision = "009_tenant_login_password"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_admins",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.String(256), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("full_name", sa.String(256), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="support"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("idx_platform_admins_email", "platform_admins", ["email"])


def downgrade() -> None:
    op.drop_index("idx_platform_admins_email", table_name="platform_admins")
    op.drop_table("platform_admins")
