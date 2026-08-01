"""Tenant.plan mutation paths: the Stripe webhook sync fix and the new
landlord plan-override endpoint (admin.py's ``update_tenant_plan``).

Regression coverage for a real gap found in production: the Stripe webhook
handler (tasks/billing.py) updated ``Subscription.plan`` on
``customer.subscription.updated`` but never ``Tenant.plan`` — the field
every feature check (``hasFeature()``, ``require_feature()``, the JWT
``plan`` claim) actually reads. A tenant who paid to upgrade kept their old
plan's access forever. Separately, there was no way for a platform admin to
fix or override a tenant's plan by hand either.
"""

import random
import uuid

import pytest
from httpx import AsyncClient

_PASSWORD = "TenantPlanTest123!"


def _fake_client_ip() -> str:
    return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


async def _register(client: AsyncClient) -> tuple[dict, str]:
    suffix = uuid.uuid4().hex[:10]
    email = f"tenant-plan-{suffix}@example.com"
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": _PASSWORD,
            "full_name": "Tenant Plan Test",
            "company_name": f"Tenant Plan Co {suffix}",
        },
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert resp.status_code == 201, resp.text
    tenant_id = resp.json()["tenant_id"]

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": _PASSWORD},
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    return headers, tenant_id


async def _create_platform_admin(role: str) -> tuple[str, str]:
    from cios.core.database import async_session_factory
    from cios.core.security import hash_password
    from cios.models.tenant import PlatformAdmin

    suffix = uuid.uuid4().hex[:10]
    email = f"tenant-plan-admin-{suffix}@cios.ai"
    password = "PlanAdmin123!"
    async with async_session_factory() as db:
        db.add(
            PlatformAdmin(
                email=email,
                password_hash=hash_password(password),
                full_name="Plan Admin",
                role=role,
            )
        )
        await db.commit()
    return email, password


async def _admin_login(client: AsyncClient, email: str, password: str) -> dict:
    login = await client.post(
        "/api/v1/admin/auth/login", json={"email": email, "password": password}
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.anyio
async def test_admin_can_change_tenant_plan_and_it_actually_gates_features(client: AsyncClient):
    tenant_headers, tenant_id = await _register(client)

    # trial (register's default) is starter-equivalent — Award Simulator is
    # growth-and-up, so this must be forbidden before any plan change.
    denied = await client.get("/api/v1/award-simulations", headers=tenant_headers)
    assert denied.status_code == 403, denied.text

    support_email, support_password = await _create_platform_admin("support")
    support_headers = await _admin_login(client, support_email, support_password)

    # "support" role is read-only — same restriction as suspend/activate.
    forbidden = await client.post(
        f"/api/v1/admin/tenants/{tenant_id}/plan",
        json={"plan": "growth"},
        headers=support_headers,
    )
    assert forbidden.status_code == 403, forbidden.text

    admin_email, admin_password = await _create_platform_admin("admin")
    admin_headers = await _admin_login(client, admin_email, admin_password)

    bad_plan = await client.post(
        f"/api/v1/admin/tenants/{tenant_id}/plan",
        json={"plan": "not-a-real-plan"},
        headers=admin_headers,
    )
    assert bad_plan.status_code == 422, bad_plan.text

    changed = await client.post(
        f"/api/v1/admin/tenants/{tenant_id}/plan",
        json={"plan": "growth"},
        headers=admin_headers,
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["plan"] == "growth"

    detail = await client.get(f"/api/v1/admin/tenants/{tenant_id}", headers=admin_headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["tenant"]["plan"] == "growth"

    audit = await client.get(f"/api/v1/admin/tenants/{tenant_id}/audit-log", headers=admin_headers)
    assert audit.status_code == 200, audit.text
    entries = [e for e in audit.json()["items"] if e["action"] == "tenant.plan_changed"]
    assert len(entries) == 1
    assert entries[0]["extra_metadata"]["platform_admin_email"] == admin_email
    assert entries[0]["changes"] == {"old_plan": "trial", "new_plan": "growth"}


@pytest.mark.anyio
async def test_stripe_subscription_updated_webhook_syncs_tenant_plan(client: AsyncClient):
    """The actual bug: Subscription.plan updating is not enough — feature
    gating reads Tenant.plan, so the webhook handler must update both."""
    from cios.core.database import async_session_factory
    from cios.models.subscription import Subscription
    from cios.models.tenant import Tenant
    from cios.tasks.billing import _handle_async

    _, tenant_id = await _register(client)
    stripe_sub_id = f"sub_{uuid.uuid4().hex[:16]}"

    async with async_session_factory() as db:
        tenant = await db.get(Tenant, uuid.UUID(tenant_id))
        assert tenant.plan == "trial"
        db.add(
            Subscription(
                tenant_id=uuid.UUID(tenant_id),
                plan="starter",
                status="active",
                stripe_subscription_id=stripe_sub_id,
            )
        )
        await db.commit()

    result = await _handle_async(
        "customer.subscription.updated",
        {"id": stripe_sub_id, "status": "active", "metadata": {"plan": "growth"}},
    )
    assert result["processed"] is True

    async with async_session_factory() as db:
        tenant = await db.get(Tenant, uuid.UUID(tenant_id))
        assert tenant.plan == "growth"

        from sqlalchemy import select

        sub = (
            await db.execute(
                select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
            )
        ).scalar_one()
        assert sub.plan == "growth"
        assert sub.status == "active"
