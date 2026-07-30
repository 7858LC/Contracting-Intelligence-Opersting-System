"""V&V Campaign 4 (Security & Tenant Isolation) — proves a landlord
suspending a tenant actually revokes access, not just flips a display flag.

Found live: /auth/login already re-checked tenant.is_active on every new
login, but /auth/refresh minted fresh access+refresh tokens straight from
the OLD refresh token's stale claims with no DB lookup at all. Since refresh
tokens live 30 days (settings.jwt_refresh_expiry_days) and the frontend
silently calls /auth/refresh on every 401, a suspended tenant already
holding a refresh token would keep working, invisibly, for up to a month
after being suspended — the landlord console would show "Suspended" while
the tenant's own session never noticed.
"""

from __future__ import annotations

import random
import uuid

import pytest
from httpx import AsyncClient


def _fake_client_ip() -> str:
    return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


async def _register(client: AsyncClient) -> dict:
    suffix = uuid.uuid4().hex[:10]
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"suspend-{suffix}@example.com",
            "password": "SuspendTest123!",
            "full_name": "Suspension Test",
            "company_name": f"Suspension Test Co {suffix}",
        },
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _platform_admin_headers(client: AsyncClient) -> dict:
    from cios.core.database import async_session_factory
    from cios.core.security import hash_password
    from cios.models.tenant import PlatformAdmin

    suffix = uuid.uuid4().hex[:10]
    email = f"suspend-admin-{suffix}@cios.ai"
    async with async_session_factory() as db:
        db.add(
            PlatformAdmin(
                email=email,
                password_hash=hash_password("SuspendAdmin123!"),
                full_name="Suspend Test Admin",
                role="admin",
            )
        )
        await db.commit()

    login = await client.post(
        "/api/v1/admin/auth/login", json={"email": email, "password": "SuspendAdmin123!"}
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.anyio
async def test_suspended_tenant_cannot_refresh_an_already_issued_token(client: AsyncClient):
    tenant = await _register(client)
    refresh_token = tenant["refresh_token"]
    tenant_id = tenant["tenant_id"]

    # Sanity: refresh works normally while the tenant is active.
    ok_refresh = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert ok_refresh.status_code == 200, ok_refresh.text
    refresh_token = ok_refresh.json()["refresh_token"]

    admin_headers = await _platform_admin_headers(client)
    suspend = await client.post(f"/api/v1/admin/tenants/{tenant_id}/suspend", headers=admin_headers)
    assert suspend.status_code == 200, suspend.text
    assert suspend.json()["is_active"] is False

    # The tenant's already-issued refresh token must now be rejected, not
    # silently honored for the remainder of its 30-day lifetime.
    blocked_refresh = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert blocked_refresh.status_code == 403, blocked_refresh.text

    # Re-activating must restore it.
    reactivate = await client.post(
        f"/api/v1/admin/tenants/{tenant_id}/activate", headers=admin_headers
    )
    assert reactivate.status_code == 200, reactivate.text

    restored_refresh = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert restored_refresh.status_code == 200, restored_refresh.text
