"""023 — password_reset_tokens.

There was no password-reset flow anywhere in the product — no endpoint, no
frontend page, not even an admin-side way to reset a tenant member's
password. POST /auth/login's own "Invalid credentials" path can only ever
mean a genuine email/password mismatch (email case is already normalized
on both sides), so a user who forgets or mistypes their password had no
self-serve way back into their account.

Not RLS-scoped, same as tenant_invites — looked up by token alone from an
unauthenticated request, before any tenant context exists.

Revision ID: 023_password_reset_tokens
Revises: 022_tenant_onboarding_progress
Create Date: 2026-08-01
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "023_password_reset_tokens"
down_revision = "022_tenant_onboarding_progress"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_member_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenant_members.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token", sa.String(256), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index(
        "ix_password_reset_tokens_tenant_member_id",
        "password_reset_tokens",
        ["tenant_member_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_tenant_member_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
