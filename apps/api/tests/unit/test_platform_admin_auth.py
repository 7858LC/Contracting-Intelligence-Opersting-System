"""Tests for the landlord/platform-admin auth boundary.

Verifies the two audiences (tenant users vs. platform admins) are genuinely
non-interchangeable: a stolen tenant token must not work as landlord access,
and a landlord token must not work as tenant access.
"""

import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/test")
os.environ.setdefault("JWT_SECRET", "test_secret_minimum_32_characters_long")
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)
os.environ.setdefault("ANTHROPIC_API_KEY", "test_key")

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from cios.core.dependencies import (
    CurrentPlatformAdmin,
    get_current_platform_admin,
    get_current_user,
    require_platform_operator,
)
from cios.core.security import create_access_token


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


_UUID_1 = "11111111-1111-1111-1111-111111111111"
_UUID_2 = "22222222-2222-2222-2222-222222222222"

_TENANT_TOKEN = create_access_token(
    {"sub": _UUID_1, "tenant_id": _UUID_2, "email": "u@x.com", "role": "owner", "plan": "trial"}
)
_ADMIN_TOKEN = create_access_token(
    {
        "sub": _UUID_1,
        "scope": "platform_admin",
        "email": "ops@cios.ai",
        "full_name": "Ops Person",
        "role": "support",
    }
)


@pytest.mark.asyncio
async def test_tenant_token_rejected_as_platform_admin():
    with pytest.raises(HTTPException) as exc:
        await get_current_platform_admin(_bearer(_TENANT_TOKEN))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_platform_admin_token_rejected_as_tenant_auth():
    # No tenant_id claim on a landlord token, so get_current_user rejects it
    # before ever touching the db session — db=None is fine here.
    with pytest.raises(HTTPException) as exc:
        await get_current_user(_bearer(_ADMIN_TOKEN), db=None)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_platform_admin_token_accepted_as_landlord_auth():
    admin = await get_current_platform_admin(_bearer(_ADMIN_TOKEN))
    assert admin.email == "ops@cios.ai"
    assert admin.role == "support"


def test_support_role_cannot_operate():
    admin = CurrentPlatformAdmin(admin_id="x", email="e", full_name="n", role="support")
    assert admin.can_operate is False


def test_admin_role_can_operate():
    admin = CurrentPlatformAdmin(admin_id="x", email="e", full_name="n", role="admin")
    assert admin.can_operate is True


@pytest.mark.asyncio
async def test_require_platform_operator_rejects_support_role():
    admin = CurrentPlatformAdmin(admin_id="x", email="e", full_name="n", role="support")
    with pytest.raises(HTTPException) as exc:
        await require_platform_operator(admin)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_platform_operator_accepts_admin_role():
    admin = CurrentPlatformAdmin(admin_id="x", email="e", full_name="n", role="admin")
    result = await require_platform_operator(admin)
    assert result is admin
