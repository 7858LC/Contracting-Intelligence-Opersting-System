"""V&V Campaign 4 (Security & Tenant Isolation) — proves isolation holds at
the HTTP boundary a real client actually hits, not just at the raw-SQL layer
test_tenant_isolation.py exercises. Two real tenants, real JWTs, real
endpoints: does Tenant B's own valid token ever let it reach Tenant A's data?

Complements, not replaces, test_tenant_isolation.py — that file proves the
RLS backstop itself works; this proves the endpoints in front of it don't
have their own tenant-scoping bug that RLS happens to be masking (e.g. a
route using a raw connection outside the request-scoped session that never
had app.current_tenant set, or a lookup keyed only by primary key with no
tenant_id filter at all).
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
            "email": f"xtenant-{suffix}@example.com",
            "password": "CrossTenant123!",
            "full_name": "Cross Tenant Test",
            "company_name": f"Cross Tenant Co {suffix}",
        },
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_tenant_cannot_read_another_tenants_opportunity_by_id(client: AsyncClient):
    a_headers = await _register(client)
    b_headers = await _register(client)

    create = await client.post(
        "/api/v1/opportunities",
        headers=a_headers,
        json={"title": "Tenant A Only — Cross-Tenant HTTP Test", "agency": "Test Agency"},
    )
    assert create.status_code == 201, create.text
    opp_id = create.json()["id"]

    # Owning tenant can read it.
    own_read = await client.get(f"/api/v1/opportunities/{opp_id}", headers=a_headers)
    assert own_read.status_code == 200

    # A different tenant, with its own perfectly valid token, must not be
    # able to reach it by ID — 404 (not 403), so existence isn't leaked either.
    cross_read = await client.get(f"/api/v1/opportunities/{opp_id}", headers=b_headers)
    assert cross_read.status_code == 404, cross_read.text


@pytest.mark.anyio
async def test_tenant_cannot_modify_another_tenants_opportunity(client: AsyncClient):
    a_headers = await _register(client)
    b_headers = await _register(client)

    create = await client.post(
        "/api/v1/opportunities",
        headers=a_headers,
        json={"title": "Tenant A Only — Cross-Tenant Write Test", "agency": "Test Agency"},
    )
    assert create.status_code == 201, create.text
    opp_id = create.json()["id"]

    cross_patch = await client.patch(
        f"/api/v1/opportunities/{opp_id}", headers=b_headers, json={"status": "closed"}
    )
    assert cross_patch.status_code == 404, cross_patch.text

    # Confirm it's actually untouched, from the owning tenant's own view.
    still_open = await client.get(f"/api/v1/opportunities/{opp_id}", headers=a_headers)
    assert still_open.json()["status"] != "closed"


@pytest.mark.anyio
async def test_tenant_list_endpoint_never_returns_another_tenants_rows(client: AsyncClient):
    a_headers = await _register(client)
    b_headers = await _register(client)

    create = await client.post(
        "/api/v1/opportunities",
        headers=a_headers,
        json={"title": "Tenant A Only — Cross-Tenant List Test", "agency": "Test Agency"},
    )
    assert create.status_code == 201, create.text
    opp_id = create.json()["id"]

    listing = await client.get("/api/v1/opportunities", headers=b_headers)
    assert listing.status_code == 200
    assert not any(item["id"] == opp_id for item in listing.json()["items"])
