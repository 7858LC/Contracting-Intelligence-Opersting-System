"""Integrated module testing — freeze item #5's other half.

test_module_smoke.py proves each module works in isolation. This proves they
work *together*: a realistic capture workflow chained end to end across
modules through the real HTTP/API layer (not calling service internals
directly), plus that tenant isolation holds through that same layer — a
second tenant must never see the first tenant's data via any of the list
endpoints exercised here. test_tenant_isolation.py already proves RLS holds
at the database level directly; this proves the API layer actually uses it.
"""

from __future__ import annotations

import random
import uuid

import pytest
from httpx import AsyncClient

# anyio_backend, _fresh_connections_per_test, and client fixtures all come
# from tests/integration/conftest.py — every test file in this directory
# shares them.


def _fake_client_ip() -> str:
    """A distinct X-Forwarded-For per call so /auth/register's Redis-backed
    rate limiter (keyed by client IP, 5 requests/5min) doesn't treat this
    whole test module — which all run from the same test-harness IP — as one
    client hammering the endpoint."""
    return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


_PIPELINE_PASSWORD = "PipelineTest123!"


async def _register(client: AsyncClient, label: str) -> dict:
    """Capabilities, Competitors, Teaming, and Award Simulator are all
    gated Growth+ via require_feature() (api/v1/router.py), and this
    file exercises all four — register always issues plan="trial", so this
    bumps the tenant's plan and logs in again for a token that actually
    carries it (see conftest's upgrade_tenant_plan)."""
    from tests.integration.conftest import upgrade_tenant_plan

    suffix = uuid.uuid4().hex[:10]
    email = f"pipeline-{label}-{suffix}@example.com"
    ip_header = {"X-Forwarded-For": _fake_client_ip()}
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": _PIPELINE_PASSWORD,
            "full_name": f"Pipeline {label}",
            "company_name": f"Pipeline {label} Co {suffix}",
        },
        headers=ip_header,
    )
    assert resp.status_code == 201, resp.text
    await upgrade_tenant_plan(resp.json()["tenant_id"])

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": _PIPELINE_PASSWORD},
        headers=ip_header,
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.anyio
async def test_capture_workflow_chains_across_modules(client: AsyncClient):
    """Register → opportunity → capabilities/competitors/teaming/past-performance
    attached to it → bid decision → award simulation → Winning Profile Hypothesis.
    Nothing here asserts AI output content (Celery tasks are queued, not run
    inline, in this environment) — it asserts the modules compose without
    breaking each other's data or tenant scoping."""
    headers = await _register(client, "capture")

    opp = await client.post(
        "/api/v1/opportunities",
        headers=headers,
        json={
            "title": "Cross-Module Pipeline Opportunity",
            "agency": "Department of Testing",
            "estimated_value_max": 5_000_000,
        },
    )
    assert opp.status_code == 201, opp.text
    opp_id = opp.json()["id"]

    capability = await client.post(
        "/api/v1/capabilities",
        headers=headers,
        json={"name": "DevSecOps", "category": "technical", "is_certified": True},
    )
    assert capability.status_code == 200, capability.text

    competitor = await client.post(
        "/api/v1/competitors",
        headers=headers,
        json={"company_name": "Incumbent Rival Corp", "threat_level": "high"},
    )
    assert competitor.status_code == 200, competitor.text
    competitor_id = competitor.json()["id"]

    intel = await client.post(
        f"/api/v1/competitors/{competitor_id}/intel",
        headers=headers,
        json={"intel_type": "pricing", "content": "Historically prices 8% below market."},
    )
    assert intel.status_code == 200, intel.text

    partner = await client.post(
        "/api/v1/teaming/partners",
        headers=headers,
        json={"company_name": "Subcontractor Partner LLC", "relationship_strength": 4},
    )
    assert partner.status_code == 200, partner.text

    past_perf = await client.post(
        "/api/v1/past-performance",
        headers=headers,
        json={
            "contract_title": "Prior Agency IT Support",
            "customer_name": "Department of Testing",
            "cpars_rating": "exceptional",
        },
    )
    assert past_perf.status_code == 200, past_perf.text

    bid_decision = await client.post(
        "/api/v1/bid-decisions", headers=headers, json={"opportunity_id": opp_id}
    )
    assert bid_decision.status_code == 202, bid_decision.text

    simulation = await client.post(
        "/api/v1/award-simulations",
        headers=headers,
        json={"opportunity_id": opp_id, "name": "Pipeline Simulation"},
    )
    assert simulation.status_code == 202, simulation.text

    wph = await client.post(
        "/api/v1/winning-profile/sample", headers=headers, params={"run": "true"}
    )
    assert wph.status_code == 201, wph.text
    assert wph.json()["profile"]["attribute_count"] > 0

    # Everything just created is visible back through its own module's list endpoint.
    opps = await client.get("/api/v1/opportunities", headers=headers)
    assert any(o["id"] == opp_id for o in opps.json()["items"])

    gaps = await client.get("/api/v1/capabilities/gaps", headers=headers)
    assert gaps.status_code == 200

    competitors = await client.get("/api/v1/competitors", headers=headers)
    assert any(c["id"] == competitor_id for c in competitors.json()["competitors"])


@pytest.mark.anyio
async def test_tenant_isolation_holds_across_every_module_list_endpoint(client: AsyncClient):
    """API-level companion to test_tenant_isolation.py's direct-DB RLS proof:
    tenant A's data must be invisible to tenant B through every list endpoint
    exercised by the capture workflow above, not just one."""
    headers_a = await _register(client, "iso-a")
    headers_b = await _register(client, "iso-b")

    opp = await client.post(
        "/api/v1/opportunities",
        headers=headers_a,
        json={"title": "Tenant A Only Opportunity"},
    )
    assert opp.status_code == 201
    opp_id = opp.json()["id"]

    await client.post(
        "/api/v1/capabilities", headers=headers_a, json={"name": "Tenant A Cap", "category": "x"}
    )
    await client.post(
        "/api/v1/competitors", headers=headers_a, json={"company_name": "Tenant A Rival"}
    )
    await client.post(
        "/api/v1/teaming/partners", headers=headers_a, json={"company_name": "Tenant A Partner"}
    )
    await client.post(
        "/api/v1/past-performance",
        headers=headers_a,
        json={"contract_title": "Tenant A Contract", "customer_name": "Agency A"},
    )

    # Tenant B must see none of it.
    b_opps = await client.get("/api/v1/opportunities", headers=headers_b)
    assert opp_id not in {o["id"] for o in b_opps.json()["items"]}

    b_caps = await client.get("/api/v1/capabilities", headers=headers_b)
    assert all(c["name"] != "Tenant A Cap" for c in b_caps.json()["capabilities"])

    b_competitors = await client.get("/api/v1/competitors", headers=headers_b)
    assert all(c["company_name"] != "Tenant A Rival" for c in b_competitors.json()["competitors"])

    b_partners = await client.get("/api/v1/teaming/partners", headers=headers_b)
    assert all(p["company_name"] != "Tenant A Partner" for p in b_partners.json()["partners"])

    b_pp = await client.get("/api/v1/past-performance", headers=headers_b)
    assert all(p["contract_title"] != "Tenant A Contract" for p in b_pp.json()["items"])

    # And tenant B can't reach tenant A's opportunity by ID either.
    direct = await client.get(f"/api/v1/opportunities/{opp_id}", headers=headers_b)
    assert direct.status_code == 404
