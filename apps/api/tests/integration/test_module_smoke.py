"""Module smoke tests — freeze item #5, closing gate of the freeze sequence.

One representative request per module: does it register, accept a minimal
valid payload, and respond without a 5xx? This is not a correctness suite —
each module's own unit/integration tests (e.g. test_winning_profile_engine.py,
test_tenant_isolation.py) cover behavior. This catches wiring regressions:
a broken import, a missing router registration, a model/schema mismatch —
the class of bug that only surfaces when the endpoint is actually hit.

Requires a real, migrated Postgres + reachable Redis (Celery broker for the
modules that queue async work) — see tests/integration/test_api_health.py
for why these tests can't run against a mocked DB.
"""

from __future__ import annotations

import os
import uuid

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://cios_user:cios_pass@localhost:5432/cios_test"
)
os.environ.setdefault("JWT_SECRET", "test_secret_minimum_32_characters_long")
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)
os.environ.setdefault("ANTHROPIC_API_KEY", "test_key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("TENANT_KEY_DERIVATION_SALT", "test_salt")

import random

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
async def _fresh_connections_per_test():
    """The DB engine's and Redis client's pooled connections are bound to
    whichever event loop first used them; pytest-asyncio gives each test its
    own loop, so both must be reset before and after every test here (same
    reasoning as test_tenant_isolation.py's engine-only version — this file
    also touches Redis via the rate limiter)."""
    from cios.core.database import engine
    from cios.core.redis import redis_client

    await engine.dispose()
    await redis_client.aclose()
    yield
    await engine.dispose()
    await redis_client.aclose()


@pytest.fixture
async def client():
    from cios.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def _fake_client_ip() -> str:
    """A distinct X-Forwarded-For per call so /auth/register's Redis-backed
    rate limiter (keyed by client IP, 5 requests/5min — see
    core/rate_limit.py) doesn't treat this whole test module, which all run
    from the same test-harness IP, as one client hammering the endpoint."""
    return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


async def _register(client: AsyncClient) -> dict:
    """Register a fresh tenant + owner and return auth headers. Exercising this
    on every smoke test is itself a smoke test of the auth module (including
    the password hash/verify path)."""
    suffix = uuid.uuid4().hex[:10]
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"smoke-{suffix}@example.com",
            "password": "SmokeTest123!",
            "full_name": "Smoke Test",
            "company_name": f"Smoke Co {suffix}",
        },
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_opportunity(client: AsyncClient, headers: dict) -> str:
    resp = await client.post(
        "/api/v1/opportunities",
        headers=headers,
        json={"title": "Smoke Test Opportunity", "agency": "Test Agency"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.mark.anyio
async def test_auth_register_and_login_round_trip(client: AsyncClient):
    """Module: Auth. Also the regression test for the password-verification fix —
    a second login with the WRONG password must be rejected."""
    suffix = uuid.uuid4().hex[:10]
    email = f"smoke-auth-{suffix}@example.com"
    ip_header = {"X-Forwarded-For": _fake_client_ip()}
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "CorrectHorse123!",
            "full_name": "Auth Smoke",
            "company_name": f"Auth Smoke Co {suffix}",
        },
        headers=ip_header,
    )
    assert register.status_code == 201, register.text

    good_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "CorrectHorse123!"},
        headers=ip_header,
    )
    assert good_login.status_code == 200, good_login.text

    bad_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPassword!"},
        headers=ip_header,
    )
    assert bad_login.status_code == 401


@pytest.mark.anyio
async def test_tenants_module_smoke(client: AsyncClient):
    headers = await _register(client)
    resp = await client.get("/api/v1/tenants/profile", headers=headers)
    assert resp.status_code == 200, resp.text

    members = await client.get("/api/v1/tenants/members", headers=headers)
    assert members.status_code == 200, members.text


@pytest.mark.anyio
async def test_opportunities_module_smoke(client: AsyncClient):
    headers = await _register(client)
    opp_id = await _create_opportunity(client, headers)

    resp = await client.get("/api/v1/opportunities", headers=headers)
    assert resp.status_code == 200, resp.text
    assert any(item["id"] == opp_id for item in resp.json()["items"])


@pytest.mark.anyio
async def test_bid_decisions_module_smoke(client: AsyncClient):
    headers = await _register(client)
    opp_id = await _create_opportunity(client, headers)

    resp = await client.post(
        "/api/v1/bid-decisions", headers=headers, json={"opportunity_id": opp_id}
    )
    assert resp.status_code == 202, resp.text
    assert resp.json()["status"] == "queued"


@pytest.mark.anyio
async def test_capabilities_module_smoke(client: AsyncClient):
    headers = await _register(client)
    resp = await client.post(
        "/api/v1/capabilities",
        headers=headers,
        json={"name": "Cloud Migration", "category": "technical"},
    )
    assert resp.status_code == 200, resp.text

    gaps = await client.get("/api/v1/capabilities/gaps", headers=headers)
    assert gaps.status_code == 200, gaps.text


@pytest.mark.anyio
async def test_past_performance_module_smoke(client: AsyncClient):
    headers = await _register(client)
    resp = await client.post(
        "/api/v1/past-performance",
        headers=headers,
        json={"contract_title": "Smoke Contract", "customer_name": "Smoke Agency"},
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.anyio
async def test_teaming_module_smoke(client: AsyncClient):
    headers = await _register(client)
    resp = await client.post(
        "/api/v1/teaming/partners", headers=headers, json={"company_name": "Smoke Partner LLC"}
    )
    assert resp.status_code == 200, resp.text

    partners = await client.get("/api/v1/teaming/partners", headers=headers)
    assert partners.status_code == 200, partners.text


@pytest.mark.anyio
async def test_competitors_module_smoke(client: AsyncClient):
    headers = await _register(client)
    resp = await client.post(
        "/api/v1/competitors", headers=headers, json={"company_name": "Smoke Rival Inc"}
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.anyio
async def test_award_simulator_module_smoke(client: AsyncClient):
    headers = await _register(client)
    opp_id = await _create_opportunity(client, headers)

    resp = await client.post(
        "/api/v1/award-simulations",
        headers=headers,
        json={"opportunity_id": opp_id, "name": "Smoke Simulation"},
    )
    assert resp.status_code == 202, resp.text
    assert resp.json()["status"] == "queued"


@pytest.mark.anyio
async def test_knowledge_vault_module_smoke(client: AsyncClient):
    headers = await _register(client)
    resp = await client.get("/api/v1/knowledge-vault", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["items"] == []


@pytest.mark.anyio
async def test_agent_runs_module_smoke(client: AsyncClient):
    headers = await _register(client)
    resp = await client.get("/api/v1/agent-runs", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["items"] == []


@pytest.mark.anyio
async def test_subscriptions_module_smoke(client: AsyncClient):
    headers = await _register(client)
    current = await client.get("/api/v1/subscriptions/current", headers=headers)
    assert current.status_code == 200, current.text
    assert current.json()["plan"] == "trial"

    invoices = await client.get("/api/v1/subscriptions/invoices", headers=headers)
    assert invoices.status_code == 200, invoices.text


@pytest.mark.anyio
async def test_onboarding_module_smoke(client: AsyncClient):
    headers = await _register(client)
    status_resp = await client.get("/api/v1/onboarding/status", headers=headers)
    assert status_resp.status_code == 200, status_resp.text

    step = await client.post(
        "/api/v1/onboarding/steps/company_profile",
        headers=headers,
        json={"step": "company_profile", "data": {"name": "Smoke Co"}},
    )
    assert step.status_code == 200, step.text


@pytest.mark.anyio
async def test_radar_pir_module_smoke(client: AsyncClient):
    headers = await _register(client)
    resp = await client.post(
        "/api/v1/radar/companies", headers=headers, json={"name": "Smoke Radar Target Inc"}
    )
    assert resp.status_code == 201, resp.text

    dashboard = await client.get("/api/v1/radar/dashboard", headers=headers)
    assert dashboard.status_code == 200, dashboard.text


@pytest.mark.anyio
async def test_winning_profile_module_smoke(client: AsyncClient):
    headers = await _register(client)
    resp = await client.post(
        "/api/v1/winning-profile/sample", headers=headers, params={"run": "true"}
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["profile"] is not None
    assert body["rankings"]


@pytest.mark.anyio
async def test_webhooks_module_smoke(client: AsyncClient):
    """Stripe isn't configured in the test environment — the route must fail
    clean (503) rather than 500 when it can't verify a signature it has no
    secret for."""
    resp = await client.post("/api/v1/webhooks/stripe", content=b"{}")
    assert resp.status_code == 503, resp.text


@pytest.mark.anyio
async def test_admin_landlord_module_smoke(client: AsyncClient):
    """Module: landlord/tenant-ops layer (freeze item #3). No self-service
    signup for platform admins, so provision one directly the same way
    scripts/create_platform_admin.py does."""
    from cios.core.database import async_session_factory
    from cios.core.security import hash_password
    from cios.models.tenant import PlatformAdmin

    suffix = uuid.uuid4().hex[:10]
    email = f"smoke-admin-{suffix}@cios.ai"
    async with async_session_factory() as db:
        db.add(
            PlatformAdmin(
                email=email,
                password_hash=hash_password("SmokeAdmin123!"),
                full_name="Smoke Admin",
                role="admin",
            )
        )
        await db.commit()

    login = await client.post(
        "/api/v1/admin/auth/login", json={"email": email, "password": "SmokeAdmin123!"}
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    stats = await client.get("/api/v1/admin/stats", headers=headers)
    assert stats.status_code == 200, stats.text

    tenants = await client.get("/api/v1/admin/tenants", headers=headers)
    assert tenants.status_code == 200, tenants.text

    # A tenant token must never work as landlord access, and vice versa.
    tenant_headers = await _register(client)
    denied = await client.get("/api/v1/admin/stats", headers=tenant_headers)
    assert denied.status_code == 401
