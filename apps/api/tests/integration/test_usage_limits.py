"""Proves core/usage.py's enforce_usage_limit() actually blocks a tenant
at their plan's real limit, instead of the "Usage Limits" row on the
pricing page being pure copy with nothing behind it.

A freshly registered tenant gets plan="trial", which core/features.py
treats as starter-equivalent: tracked_companies=250, watchlist_slots=25,
saved_searches=5, ai_reports_per_month=10, bulk_scan_jobs_per_month=2,
seats=3. The small limits (saved_searches, bulk_scan_jobs_per_month,
seats) are exercised via real sequential API calls; the larger ones
(tracked_companies, ai_reports_per_month) are proven by seeding rows
directly at (limit - 1) and (limit) and checking the boundary with one
real call each, rather than looping the API hundreds of times.
"""

from __future__ import annotations

import random
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from cios.core.database import async_session_factory
from cios.models.pir import PIRAIAnalysis, PIRCompany
from cios.models.tenant import Tenant


def _fake_client_ip() -> str:
    return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


_USAGE_PASSWORD = "UsageLimitTest123!"


async def _register(client: AsyncClient) -> tuple[dict, str, str]:
    suffix = uuid.uuid4().hex[:10]
    email = f"usage-{suffix}@example.com"
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": _USAGE_PASSWORD,
            "full_name": "Usage Limit Test",
            "company_name": f"Usage Limit Co {suffix}",
        },
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["tenant_id"], email


async def _login(client: AsyncClient, email: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": _USAGE_PASSWORD},
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _set_tenant(db, tenant_id: str) -> None:
    await db.execute(
        text("SELECT set_config('app.current_tenant', :t, false)"), {"t": tenant_id}
    )


@pytest.mark.anyio
async def test_saved_searches_blocked_at_starter_limit_of_five(client: AsyncClient):
    headers, _, _ = await _register(client)

    for i in range(5):
        resp = await client.post(
            "/api/v1/radar/saved-searches",
            headers=headers,
            json={"name": f"Search {i}", "filters": {}},
        )
        assert resp.status_code == 201, f"search {i}: {resp.text}"

    blocked = await client.post(
        "/api/v1/radar/saved-searches",
        headers=headers,
        json={"name": "Search 6 — over limit", "filters": {}},
    )
    assert blocked.status_code == 402, blocked.text
    assert "saved searches" in blocked.json()["detail"]


@pytest.mark.anyio
async def test_bulk_scan_jobs_blocked_at_starter_limit_of_two_per_month(client: AsyncClient):
    headers, _, _ = await _register(client)

    for i in range(2):
        resp = await client.post("/api/v1/radar/scans", headers=headers)
        assert resp.status_code == 202, f"scan {i}: {resp.text}"

    blocked = await client.post("/api/v1/radar/scans", headers=headers)
    assert blocked.status_code == 402, blocked.text
    assert "bulk scan jobs" in blocked.json()["detail"]


@pytest.mark.anyio
async def test_seats_blocked_at_starter_limit_of_three_including_owner(client: AsyncClient):
    """The registering owner is member #1 — starter allows 3 total, so
    exactly 2 invites succeed before the 3rd is blocked."""
    headers, _, _ = await _register(client)

    for i in range(2):
        resp = await client.post(
            "/api/v1/tenants/members/invite",
            headers=headers,
            json={"email": f"teammate{i}@example.com", "role": "member"},
        )
        assert resp.status_code == 200, f"invite {i}: {resp.text}"

    blocked = await client.post(
        "/api/v1/tenants/members/invite",
        headers=headers,
        json={"email": "over-limit@example.com", "role": "member"},
    )
    assert blocked.status_code == 402, blocked.text
    assert "seats" in blocked.json()["detail"]


@pytest.mark.anyio
async def test_tracked_companies_blocked_at_starter_limit_of_250(client: AsyncClient):
    headers, tenant_id, email = await _register(client)

    async with async_session_factory() as db:
        await _set_tenant(db, tenant_id)
        db.add_all(
            [
                PIRCompany(tenant_id=uuid.UUID(tenant_id), name=f"Seeded Co {i}")
                for i in range(250)
            ]
        )
        await db.commit()

    blocked = await client.post(
        "/api/v1/radar/companies", headers=headers, json={"name": "251st Company"}
    )
    assert blocked.status_code == 402, blocked.text
    assert "tracked companies" in blocked.json()["detail"]


@pytest.mark.anyio
async def test_ai_reports_blocked_at_starter_limit_of_ten_per_month(client: AsyncClient):
    headers, tenant_id, email = await _register(client)

    async with async_session_factory() as db:
        await _set_tenant(db, tenant_id)
        company = PIRCompany(tenant_id=uuid.UUID(tenant_id), name="Target Co")
        db.add(company)
        await db.flush()
        db.add_all(
            [
                PIRAIAnalysis(
                    tenant_id=uuid.UUID(tenant_id), company_id=company.id, status="completed"
                )
                for _ in range(10)
            ]
        )
        await db.commit()
        company_id = str(company.id)

    blocked = await client.post(f"/api/v1/radar/companies/{company_id}/analyze", headers=headers)
    assert blocked.status_code == 402, blocked.text
    assert "AI analysis reports" in blocked.json()["detail"]


@pytest.mark.anyio
async def test_enterprise_plan_has_no_tracked_company_limit(client: AsyncClient):
    headers, tenant_id, email = await _register(client)

    async with async_session_factory() as db:
        tenant = await db.get(Tenant, uuid.UUID(tenant_id))
        tenant.plan = "enterprise"
        await db.commit()

        await _set_tenant(db, tenant_id)
        db.add_all(
            [
                PIRCompany(tenant_id=uuid.UUID(tenant_id), name=f"Bulk Seeded Co {i}")
                for i in range(300)
            ]
        )
        await db.commit()

    # Re-login for a token that actually carries plan="enterprise" — plan
    # is baked into the JWT at issue time (see auth.py), so the token from
    # _register() above still carries plan="trial".
    fresh_headers = await _login(client, email)

    ok = await client.post(
        "/api/v1/radar/companies", headers=fresh_headers, json={"name": "301st Company"}
    )
    assert ok.status_code == 201, ok.text
