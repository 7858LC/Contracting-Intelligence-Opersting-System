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

import random
import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

# anyio_backend, _fresh_connections_per_test, and client fixtures all come
# from tests/integration/conftest.py — every test file in this directory
# shares them.


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
        "/api/v1/bid-decisions",
        headers=headers,
        json={"opportunity_id": opp_id, "go_no_go_threshold": 70},
    )
    assert resp.status_code == 202, resp.text
    assert resp.json()["status"] == "queued"

    # The frontend (bid-decision-view.tsx) depends on this exact response
    # shape — decision/overall_score/capability_score/risk_factors/rationale
    # are all deliberately different names from this model's own columns
    # (recommendation/composite_score/etc.), and go_no_go_threshold/
    # analyzed_at were dropped by a schema-drift migration and restored in
    # 015. A field-name mismatch here is exactly what crashed the page
    # ("u.filter is not a function") since the wrapper key didn't match either.
    listed = await client.get("/api/v1/bid-decisions", headers=headers)
    assert listed.status_code == 200, listed.text
    items = listed.json()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["opportunity_title"]
    assert item["go_no_go_threshold"] == 70
    expected_keys = (
        "decision", "overall_score", "capability_score", "risk_factors", "rationale", "analyzed_at",
    )
    for key in expected_keys:
        assert key in item

    detail = await client.get(f"/api/v1/bid-decisions/{item['id']}", headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["opportunity_title"] == item["opportunity_title"]


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
    assert body["assessment"] is not None


@pytest.mark.anyio
async def test_wph_capture_package_module_smoke(client: AsyncClient):
    """Capture package build -> review -> approve -> publish-to-vault, on top
    of the same seeded/run sample used by the winning-profile smoke test."""
    headers = await _register(client)
    seeded = await client.post(
        "/api/v1/winning-profile/sample", headers=headers, params={"run": "true"}
    )
    assert seeded.status_code == 201, seeded.text
    sol_id = seeded.json()["solicitation_id"]

    # Generating before any package exists creates version 1, draft.
    built = await client.post(
        f"/api/v1/winning-profile/solicitations/{sol_id}/capture-package", headers=headers
    )
    assert built.status_code == 200, built.text
    package = built.json()
    assert package["version"] == 1
    assert package["status"] == "draft"
    assert package["content"]["solicitation"]["title"]
    assert package["content"]["target_assessment"] is not None
    assert package["content"]["contractor_rankings"]

    fetched = await client.get(
        f"/api/v1/winning-profile/solicitations/{sol_id}/capture-package", headers=headers
    )
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["id"] == package["id"]

    # Regenerating bumps the version and supersedes the prior one.
    rebuilt = await client.post(
        f"/api/v1/winning-profile/solicitations/{sol_id}/capture-package", headers=headers
    )
    assert rebuilt.status_code == 200, rebuilt.text
    assert rebuilt.json()["version"] == 2

    history = await client.get(
        f"/api/v1/winning-profile/solicitations/{sol_id}/capture-package/history",
        headers=headers,
    )
    assert history.status_code == 200, history.text
    assert len(history.json()["items"]) == 2

    # Publishing before approval is rejected.
    early_publish = await client.post(
        f"/api/v1/winning-profile/solicitations/{sol_id}/capture-package/publish-to-vault",
        headers=headers,
    )
    assert early_publish.status_code == 409, early_publish.text

    approved = await client.post(
        f"/api/v1/winning-profile/solicitations/{sol_id}/capture-package/approve",
        headers=headers,
        json={"review_notes": "Looks accurate, approved for the exec review."},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert approved.json()["reviewed_by"]

    published = await client.post(
        f"/api/v1/winning-profile/solicitations/{sol_id}/capture-package/publish-to-vault",
        headers=headers,
    )
    assert published.status_code == 200, published.text
    assert published.json()["knowledge_vault_document_id"]

    vault = await client.get("/api/v1/knowledge-vault", headers=headers)
    assert vault.status_code == 200, vault.text
    assert any(d["document_type"] == "capture_package" for d in vault.json()["items"])


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


@pytest.mark.anyio
async def test_research_module_smoke(client: AsyncClient):
    """Module: research (Executive Council report access, Phase 1 —
    Agency Intelligence Brief). Phase 1's tables have no tenant-facing write
    endpoints — AgencyProfile/AgencyBuyingPattern/ResearchReport are only
    ever populated by the generate_agency_intelligence_brief Celery task —
    so seed them directly, same as the admin smoke test does for
    PlatformAdmin. Also proves is_council_member actually gates access, in
    both directions, through the real grant/revoke admin endpoints."""
    from cios.core.database import async_session_factory
    from cios.core.security import hash_password
    from cios.models.research import AgencyProfile, ReportStatus, ResearchReport
    from cios.models.tenant import PlatformAdmin

    tenant_headers = await _register(client)
    profile = await client.get("/api/v1/tenants/profile", headers=tenant_headers)
    assert profile.status_code == 200, profile.text
    tenant_id = profile.json()["id"]

    suffix = uuid.uuid4().hex[:10]
    admin_email = f"smoke-research-admin-{suffix}@cios.ai"
    async with async_session_factory() as db:
        db.add(
            AgencyProfile(name=f"Smoke Agency {suffix}", usaspending_toptier_code="097")
        )
        report = ResearchReport(
            report_type="agency_intelligence_brief",
            period_label="2026-Q3",
            status=ReportStatus.PUBLISHED.value,
            title="Smoke Test Agency Intelligence Brief — 2026-Q3",
            summary="Smoke test summary.",
            content=[{"agency": "Smoke Agency", "brief": {"executive_summary": "Smoke summary."}}],
            published_at=datetime.now(UTC),
        )
        db.add(report)
        db.add(
            PlatformAdmin(
                email=admin_email,
                password_hash=hash_password("SmokeAdmin123!"),
                full_name="Smoke Research Admin",
                role="admin",
            )
        )
        await db.commit()
        report_id = str(report.id)

    # Not a Council member yet — reports are forbidden, not just empty.
    denied = await client.get("/api/v1/research/reports", headers=tenant_headers)
    assert denied.status_code == 403, denied.text

    admin_login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": admin_email, "password": "SmokeAdmin123!"},
    )
    assert admin_login.status_code == 200, admin_login.text
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    grant = await client.post(
        f"/api/v1/admin/tenants/{tenant_id}/council/grant", headers=admin_headers
    )
    assert grant.status_code == 200, grant.text
    assert grant.json()["is_council_member"] is True

    reports = await client.get("/api/v1/research/reports", headers=tenant_headers)
    assert reports.status_code == 200, reports.text
    assert any(r["id"] == report_id for r in reports.json()["items"])

    one = await client.get(f"/api/v1/research/reports/{report_id}", headers=tenant_headers)
    assert one.status_code == 200, one.text
    assert one.json()["title"] == "Smoke Test Agency Intelligence Brief — 2026-Q3"
    assert one.json()["content"][0]["agency"] == "Smoke Agency"

    revoke = await client.post(
        f"/api/v1/admin/tenants/{tenant_id}/council/revoke", headers=admin_headers
    )
    assert revoke.status_code == 200, revoke.text
    assert revoke.json()["is_council_member"] is False

    denied_again = await client.get("/api/v1/research/reports", headers=tenant_headers)
    assert denied_again.status_code == 403, denied_again.text
