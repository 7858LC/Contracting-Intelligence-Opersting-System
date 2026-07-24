"""009 — Add password_hash to tenant_members; /auth/login checked no password.

register()/login() accepted and validated a password but never hashed, stored,
or verified it — TenantMember had no password column at all, so any request
with a valid, active member email logged in as that member regardless of what
password (or none) was supplied. This closes the column-level half of that
gap; cios/api/v1/endpoints/auth.py wires hash_password/verify_password into
the two endpoints in the same change.

Existing rows get password_hash = NULL — nullable, since there is no reset
flow yet, and NULL is treated as "no usable password" (login rejected) rather
than "no password required."

Revision ID: 009_tenant_login_password
Revises: 008_wph_vehicle_contestability
Create Date: 2026-07-24
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "009_tenant_login_password"
down_revision = "008_wph_vehicle_contestability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenant_members", sa.Column("password_hash", sa.String(256), nullable=True))


def downgrade() -> None:
    op.drop_column("tenant_members", "password_hash")
