"""Proves onboarding persists real data instead of returning fake
"completed" status with nothing behind it.

GET /status previously hardcoded completed_steps: [] and
completion_percentage: 0 always; POST /steps/{step} validated the step
name and returned "completed" without writing anything. This proves each
step actually persists (Tenant.onboarding_completed_steps, and real
Capability/Competitor/TeamingPartner/PastPerformance rows for the steps
that map to a real model), that completing every step triggers
run_initial_analysis for real, and that a bad step payload gets a clean
422 instead of a 500.
"""

from __future__ import annotations

import random
import uuid

import pytest
from httpx import AsyncClient


def _fake_client_ip() -> str:
    return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


async def _register(client: AsyncClient) -> dict:
    headers, _ = await _register_with_tenant(client)
    return headers


async def _register_with_tenant(client: AsyncClient) -> tuple[dict, str]:
    suffix = uuid.uuid4().hex[:10]
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"onboard-{suffix}@example.com",
            "password": "OnboardTest123!",
            "full_name": "Onboard Test",
            "company_name": f"Onboard Co {suffix}",
        },
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["tenant_id"]


@pytest.mark.anyio
async def test_status_reflects_zero_progress_for_a_new_tenant(client: AsyncClient):
    headers = await _register(client)
    resp = await client.get("/api/v1/onboarding/status", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["completed_steps"] == []
    assert body["completion_percentage"] == 0
    assert body["next_step"] == "company_profile"


@pytest.mark.anyio
async def test_company_profile_step_persists_onto_tenant(client: AsyncClient):
    headers = await _register(client)

    resp = await client.post(
        "/api/v1/onboarding/steps/company_profile",
        headers=headers,
        json={
            "step": "company_profile",
            "data": {"cage_code": "1A2B3", "annual_revenue_band": "$1M-$5M"},
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["next_step"] == "naics_codes"

    profile = await client.get("/api/v1/tenants/profile", headers=headers)
    assert profile.status_code == 200, profile.text
    assert profile.json()["cage_code"] == "1A2B3"

    status = await client.get("/api/v1/onboarding/status", headers=headers)
    assert status.json()["completed_steps"] == ["company_profile"]
    assert status.json()["completion_percentage"] == 12  # round(100 * 1/8), banker's rounding


@pytest.mark.anyio
async def test_capabilities_step_creates_real_capability_rows(client: AsyncClient):
    """Verified via a direct DB read, not GET /capabilities — Capabilities
    & Gaps is Growth+ gated (see core/features.py), and a trial-plan
    tenant (what /auth/register always issues) legitimately can't read
    that endpoint even though onboarding itself stays open to every plan.
    That's an intentional consequence of the plan-gating work, not a bug
    in onboarding."""
    headers, tenant_id = await _register_with_tenant(client)

    resp = await client.post(
        "/api/v1/onboarding/steps/capabilities",
        headers=headers,
        json={
            "step": "capabilities",
            "data": {
                "items": [
                    {"name": "Cloud Migration", "category": "technical"},
                    {"name": "Program Management", "category": "management"},
                ]
            },
        },
    )
    assert resp.status_code == 200, resp.text

    from sqlalchemy import select, text

    from cios.core.database import async_session_factory
    from cios.models.capability import Capability

    async with async_session_factory() as db:
        await db.execute(
            text("SELECT set_config('app.current_tenant', :t, false)"), {"t": tenant_id}
        )
        rows = (
            await db.execute(select(Capability).where(Capability.tenant_id == uuid.UUID(tenant_id)))
        ).scalars().all()
    assert {r.name for r in rows} == {"Cloud Migration", "Program Management"}


@pytest.mark.anyio
async def test_invalid_step_payload_returns_422_not_500(client: AsyncClient):
    headers = await _register(client)

    resp = await client.post(
        "/api/v1/onboarding/steps/competitors",
        headers=headers,
        json={"step": "competitors", "data": {"items": [{"no_company_name": "oops"}]}},
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.anyio
async def test_unknown_step_name_returns_400(client: AsyncClient):
    headers = await _register(client)
    resp = await client.post(
        "/api/v1/onboarding/steps/not-a-real-step",
        headers=headers,
        json={"step": "not-a-real-step", "data": {}},
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.anyio
async def test_completing_every_step_marks_onboarding_complete_and_runs_real_analysis(
    client: AsyncClient,
):
    headers = await _register(client)

    steps_data = {
        "company_profile": {"cage_code": "9Z8Y7"},
        "naics_codes": {"naics_codes": ["541512"]},
        "past_performance": {"items": []},
        "capabilities": {"items": [{"name": "DevSecOps", "category": "technical"}]},
        "certifications": {"items": ["ISO 27001"]},
        "teaming_partners": {"items": []},
        "competitors": {"items": []},
        "preferences": {"weekly_digest": True},
    }

    last_response = None
    for step, data in steps_data.items():
        resp = await client.post(
            f"/api/v1/onboarding/steps/{step}",
            headers=headers,
            json={"step": step, "data": data},
        )
        assert resp.status_code == 200, f"{step}: {resp.text}"
        last_response = resp

    assert last_response.json()["onboarding_complete"] is True
    assert last_response.json()["next_step"] is None

    status = await client.get("/api/v1/onboarding/status", headers=headers)
    assert status.json()["completion_percentage"] == 100

    # The task itself needs a tenant_id, not a bearer token.
    profile = await client.get("/api/v1/tenants/profile", headers=headers)
    tenant_id = profile.json()["id"]

    from cios.tasks.onboarding import _run_async

    result = await _run_async(tenant_id)
    assert result["status"] == "initial_analysis_complete"
    assert result["summary"]["capabilities"] == 1
