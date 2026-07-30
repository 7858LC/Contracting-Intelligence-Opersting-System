"""V&V Campaign 3 (Platform Stress) — proves the platform's most expensive
endpoints actually stop a tenant that hammers them.

Production runs exactly one Celery worker at concurrency=2 (render.yaml)
shared across every tenant and every queue. Before this, nothing bounded
how often a single tenant could trigger /opportunities/{id}/analyze (6 live
Claude calls per request — the CEO Agent plus all 5 Directors) or
POST /award-simulations (claude-opus-4-8, 16k max_tokens) — a spam loop
from one tenant, malicious or just a stuck retry in some client code,
would starve every other tenant's queued work and run up unbounded
Anthropic API cost with no per-tenant cap anywhere.
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
            "email": f"ratelimit-{suffix}@example.com",
            "password": "RateLimitTest123!",
            "full_name": "Rate Limit Test",
            "company_name": f"Rate Limit Co {suffix}",
        },
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_award_simulation_creation_is_rate_limited_per_tenant(client: AsyncClient):
    headers = await _register(client)
    create_opp = await client.post(
        "/api/v1/opportunities",
        headers=headers,
        json={"title": "Rate Limit Test Opportunity", "agency": "Test Agency"},
    )
    assert create_opp.status_code == 201, create_opp.text
    opp_id = create_opp.json()["id"]

    # The limit is 10/hour (award_simulations.py's _create_rate_limit) — the
    # first 10 must succeed normally.
    for i in range(10):
        resp = await client.post(
            "/api/v1/award-simulations",
            headers=headers,
            json={"opportunity_id": opp_id, "name": f"Burst Simulation {i}"},
        )
        assert resp.status_code == 202, f"request {i}: {resp.text}"

    # The 11th in the same window must be rejected.
    blocked = await client.post(
        "/api/v1/award-simulations",
        headers=headers,
        json={"opportunity_id": opp_id, "name": "Burst Simulation 11 — should be blocked"},
    )
    assert blocked.status_code == 429, blocked.text


@pytest.mark.anyio
async def test_opportunity_analysis_is_rate_limited_per_tenant(client: AsyncClient):
    headers = await _register(client)
    create_opp = await client.post(
        "/api/v1/opportunities",
        headers=headers,
        json={"title": "Rate Limit Analyze Test Opportunity", "agency": "Test Agency"},
    )
    assert create_opp.status_code == 201, create_opp.text
    opp_id = create_opp.json()["id"]

    for i in range(10):
        resp = await client.post(f"/api/v1/opportunities/{opp_id}/analyze", headers=headers)
        assert resp.status_code == 202, f"request {i}: {resp.text}"

    blocked = await client.post(f"/api/v1/opportunities/{opp_id}/analyze", headers=headers)
    assert blocked.status_code == 429, blocked.text


@pytest.mark.anyio
async def test_rate_limit_is_scoped_per_tenant_not_global(client: AsyncClient):
    """A second tenant must not be affected by the first tenant's burst —
    this is a per-tenant limit, not an accidental global one."""
    a_headers = await _register(client)
    b_headers = await _register(client)

    create_opp = await client.post(
        "/api/v1/opportunities",
        headers=a_headers,
        json={"title": "Tenant A Burst Opportunity", "agency": "Test Agency"},
    )
    assert create_opp.status_code == 201, create_opp.text
    opp_id = create_opp.json()["id"]

    for i in range(10):
        resp = await client.post(
            "/api/v1/award-simulations",
            headers=a_headers,
            json={"opportunity_id": opp_id, "name": f"Tenant A Burst {i}"},
        )
        assert resp.status_code == 202, f"request {i}: {resp.text}"

    exhausted = await client.post(
        "/api/v1/award-simulations",
        headers=a_headers,
        json={"opportunity_id": opp_id, "name": "Tenant A Burst 11"},
    )
    assert exhausted.status_code == 429, exhausted.text

    # Tenant B, brand new, still has its own full quota.
    b_create_opp = await client.post(
        "/api/v1/opportunities",
        headers=b_headers,
        json={"title": "Tenant B Opportunity", "agency": "Test Agency"},
    )
    assert b_create_opp.status_code == 201, b_create_opp.text
    b_opp_id = b_create_opp.json()["id"]

    b_resp = await client.post(
        "/api/v1/award-simulations",
        headers=b_headers,
        json={"opportunity_id": b_opp_id, "name": "Tenant B First Simulation"},
    )
    assert b_resp.status_code == 202, b_resp.text
