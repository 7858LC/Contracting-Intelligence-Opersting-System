"""Proves require_feature() actually enforces plan tiers at the API layer.

Previously PLAN_FEATURES existed only as display metadata returned by
GET /subscriptions — nothing checked it as an authorization gate, so every
subscription tier's feature list (Competitive Intelligence, Capabilities &
Gaps, Teaming, Award Simulator — all sold as Professional+ on the pricing
page) was enforced by nothing but which sidebar link happened to render on
the frontend. core/features.py + core/dependencies.require_feature() +
the dependencies= on those routers in api/v1/router.py are the fix; this
is the regression test for it.

A freshly registered tenant gets plan="trial" (see auth.py's /register),
which core/features.py treats as starter-equivalent — no gated features.
Bumping Tenant.plan directly in the DB and logging in again (login always
re-reads tenant.plan fresh, see auth.py's /login) is how a test gets a
token for a plan tier without needing real Stripe checkout.
"""

from __future__ import annotations

import random
import uuid

import pytest
from httpx import AsyncClient

from cios.core.database import async_session_factory
from cios.models.tenant import Tenant


def _fake_client_ip() -> str:
    return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


async def _register(client: AsyncClient) -> tuple[dict, str, str]:
    suffix = uuid.uuid4().hex[:10]
    email = f"gating-{suffix}@example.com"
    password = "GatingTest123!"
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Gating Test",
            "company_name": f"Gating Co {suffix}",
        },
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["tenant_id"], email


async def _login(client: AsyncClient, email: str, password: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _set_tenant_plan(tenant_id: str, plan: str) -> None:
    async with async_session_factory() as db:
        tenant = await db.get(Tenant, uuid.UUID(tenant_id))
        tenant.plan = plan
        await db.commit()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("path", "feature"),
    [
        ("/api/v1/competitors", "competitive_intel"),
        ("/api/v1/capabilities", "capabilities"),
        ("/api/v1/teaming/partners", "teaming"),
    ],
)
async def test_trial_plan_is_blocked_from_gated_modules(
    client: AsyncClient, path: str, feature: str
):
    headers, _, _ = await _register(client)
    resp = await client.get(path, headers=headers)
    assert resp.status_code == 403, resp.text
    assert feature.replace("_", " ") in resp.json()["detail"]


@pytest.mark.anyio
async def test_award_simulator_is_available_on_every_plan_today(client: AsyncClient):
    """award_simulator is True for every tier in PLAN_FEATURES already —
    a deliberate, pre-existing value this change didn't touch (tightening
    it would take away something starter customers already have, which is
    a business call, not an engineering one). The router still carries
    require_feature("award_simulator") so the enforcement mechanism is in
    place the moment that value is ever changed."""
    headers, _, _ = await _register(client)
    resp = await client.get("/api/v1/award-simulations", headers=headers)
    assert resp.status_code == 200, resp.text


@pytest.mark.anyio
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/competitors",
        "/api/v1/capabilities",
        "/api/v1/teaming/partners",
    ],
)
async def test_professional_plan_can_reach_gated_modules(client: AsyncClient, path: str):
    headers, tenant_id, email = await _register(client)
    await _set_tenant_plan(tenant_id, "professional")

    # The trial-issued token still carries plan="trial" until re-issued —
    # confirms plan changes need a fresh token, not just a DB update.
    stale_resp = await client.get(path, headers=headers)
    assert stale_resp.status_code == 403, stale_resp.text

    fresh_headers = await _login(client, email, "GatingTest123!")
    resp = await client.get(path, headers=fresh_headers)
    assert resp.status_code == 200, resp.text


@pytest.mark.anyio
async def test_ungated_modules_stay_open_on_trial_plan(client: AsyncClient):
    """Opportunities, Winning Profile, etc. aren't part of this gate — a
    trial tenant must still be able to reach them."""
    headers, _, _ = await _register(client)
    resp = await client.get("/api/v1/opportunities", headers=headers)
    assert resp.status_code == 200, resp.text
