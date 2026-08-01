"""End-to-end proof for the WPHContractor/Competitor link and the
Competitive Intelligence /analyze pipeline built on top of it.

Covers:
1. Creating a WPH contractor with a cage_code matching an existing tracked
   Competitor auto-links them (winning_profile.py's create_contractor).
2. The manual link/unlink endpoint as the fallback when auto-match doesn't
   find one.
3. run_competitive_analysis turns a solicitation's WPHAlignment ranking
   into a front-runner + next tiers, enriched with the linked Competitor's
   intel, and auto-creates+links a Competitor for a ranked contractor that
   had none.
4. The task fails loudly (not silently) when Winning Profile hasn't been
   run yet for the opportunity, instead of completing with nothing.
"""

from __future__ import annotations

import random
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from cios.core.database import async_session_factory
from cios.models.competitor import Competitor
from cios.models.winning_profile import WPHAlignment, WPHContractor, WPHProfile, WPHSolicitation


def _fake_client_ip() -> str:
    return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


_LANDSCAPE_PASSWORD = "LandscapeTest123!"


async def _register(client: AsyncClient) -> tuple[dict, str]:
    """Competitive Intelligence is gated Professional+ via require_feature()
    (api/v1/router.py) — register always issues plan="trial", so this bumps
    the tenant's plan and logs in again for a token that actually carries
    it (see conftest's upgrade_tenant_plan)."""
    from tests.integration.conftest import upgrade_tenant_plan

    suffix = uuid.uuid4().hex[:10]
    email = f"cla-{suffix}@example.com"
    ip_header = {"X-Forwarded-For": _fake_client_ip()}
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": _LANDSCAPE_PASSWORD,
            "full_name": "Landscape Test",
            "company_name": f"Landscape Co {suffix}",
        },
        headers=ip_header,
    )
    assert resp.status_code == 201, resp.text
    tenant_id = resp.json()["tenant_id"]
    await upgrade_tenant_plan(tenant_id)

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": _LANDSCAPE_PASSWORD},
        headers=ip_header,
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, tenant_id


async def _set_tenant(db, tenant_id: str) -> None:
    await db.execute(
        text("SELECT set_config('app.current_tenant', :t, false)"), {"t": tenant_id}
    )


@pytest.mark.anyio
async def test_create_contractor_auto_links_matching_competitor_by_cage_code(
    client: AsyncClient,
):
    headers, tenant_id = await _register(client)

    comp_resp = await client.post(
        "/api/v1/competitors",
        headers=headers,
        json={"company_name": "Rival Systems LLC", "cage_code": "1AB23", "threat_level": "high"},
    )
    assert comp_resp.status_code == 200, comp_resp.text
    competitor_id = comp_resp.json()["id"]

    contractor_resp = await client.post(
        "/api/v1/winning-profile/contractors",
        headers=headers,
        json={"name": "Rival Systems LLC", "cage_code": "1AB23"},
    )
    assert contractor_resp.status_code == 201, contractor_resp.text
    assert contractor_resp.json()["competitor_id"] == competitor_id


@pytest.mark.anyio
async def test_create_contractor_with_no_matching_cage_code_leaves_unlinked(
    client: AsyncClient,
):
    headers, _ = await _register(client)
    resp = await client.post(
        "/api/v1/winning-profile/contractors",
        headers=headers,
        json={"name": "Nobody Tracks Us Inc", "cage_code": "9ZZ99"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["competitor_id"] is None


@pytest.mark.anyio
async def test_manual_link_and_unlink_competitor(client: AsyncClient):
    headers, _ = await _register(client)

    comp_resp = await client.post(
        "/api/v1/competitors", headers=headers, json={"company_name": "Manually Linked Co"}
    )
    competitor_id = comp_resp.json()["id"]

    contractor_resp = await client.post(
        "/api/v1/winning-profile/contractors", headers=headers, json={"name": "Unlinked Rival"}
    )
    contractor_id = contractor_resp.json()["id"]
    assert contractor_resp.json()["competitor_id"] is None

    linked = await client.post(
        f"/api/v1/winning-profile/contractors/{contractor_id}/link-competitor",
        headers=headers,
        json={"competitor_id": competitor_id},
    )
    assert linked.status_code == 200, linked.text
    assert linked.json()["competitor_id"] == competitor_id

    unlinked = await client.post(
        f"/api/v1/winning-profile/contractors/{contractor_id}/link-competitor",
        headers=headers,
        json={"competitor_id": None},
    )
    assert unlinked.status_code == 200, unlinked.text
    assert unlinked.json()["competitor_id"] is None


async def _seed_solicitation_profile_and_alignments(
    tenant_id: str, opportunity_id: str
) -> dict:
    """Directly construct a minimal WPH pipeline state — solicitation, a
    current profile, self + two competitor contractors, and their
    alignment rankings — bypassing the full extraction/generation pipeline
    (deterministic but not the thing under test here)."""
    async with async_session_factory() as db:
        await _set_tenant(db, tenant_id)

        sol = WPHSolicitation(
            tenant_id=uuid.UUID(tenant_id),
            opportunity_id=uuid.UUID(opportunity_id),
            title="Landscape Test Solicitation",
            agency="Test Agency",
        )
        db.add(sol)
        await db.flush()

        profile = WPHProfile(
            tenant_id=uuid.UUID(tenant_id),
            solicitation_id=sol.id,
            version=1,
            is_current=True,
        )
        db.add(profile)
        await db.flush()

        self_contractor = WPHContractor(
            tenant_id=uuid.UUID(tenant_id), name="Our Own Org", is_self=True
        )
        front_runner_contractor = WPHContractor(
            tenant_id=uuid.UUID(tenant_id), name="Front Runner Corp", cage_code="FR001"
        )
        second_tier_contractor = WPHContractor(
            tenant_id=uuid.UUID(tenant_id), name="Second Tier Inc"
        )
        db.add_all([self_contractor, front_runner_contractor, second_tier_contractor])
        await db.flush()

        # Pre-link the front-runner to a tracked Competitor to prove
        # enrichment; leave the second tier unlinked to prove auto-create.
        tracked = Competitor(
            tenant_id=uuid.UUID(tenant_id),
            company_name="Front Runner Corp",
            cage_code="FR001",
            threat_level="high",
            pricing_tendency="aggressive",
            known_strengths=["Incumbent relationships"],
        )
        db.add(tracked)
        await db.flush()
        front_runner_contractor.competitor_id = tracked.id

        db.add_all(
            [
                WPHAlignment(
                    tenant_id=uuid.UUID(tenant_id),
                    solicitation_id=sol.id,
                    profile_id=profile.id,
                    contractor_id=self_contractor.id,
                    contractor_name=self_contractor.name,
                    overall_alignment_score=60.0,
                    rank=3,
                ),
                WPHAlignment(
                    tenant_id=uuid.UUID(tenant_id),
                    solicitation_id=sol.id,
                    profile_id=profile.id,
                    contractor_id=front_runner_contractor.id,
                    contractor_name=front_runner_contractor.name,
                    overall_alignment_score=92.5,
                    rank=1,
                ),
                WPHAlignment(
                    tenant_id=uuid.UUID(tenant_id),
                    solicitation_id=sol.id,
                    profile_id=profile.id,
                    contractor_id=second_tier_contractor.id,
                    contractor_name=second_tier_contractor.name,
                    overall_alignment_score=78.0,
                    rank=2,
                ),
            ]
        )
        await db.commit()

        return {
            "solicitation_id": str(sol.id),
            "front_runner_contractor_id": str(front_runner_contractor.id),
            "second_tier_contractor_id": str(second_tier_contractor.id),
            "tracked_competitor_id": str(tracked.id),
        }


@pytest.mark.anyio
async def test_analyze_returns_front_runner_and_next_tier_excluding_self(client: AsyncClient):
    headers, tenant_id = await _register(client)

    opp_resp = await client.post(
        "/api/v1/opportunities",
        headers=headers,
        json={"title": "Landscape Test Opp", "agency": "Test Agency"},
    )
    assert opp_resp.status_code == 201, opp_resp.text
    opportunity_id = opp_resp.json()["id"]

    seeded = await _seed_solicitation_profile_and_alignments(tenant_id, opportunity_id)

    analyze_resp = await client.post(
        "/api/v1/competitors/analyze", headers=headers, json={"opportunity_id": opportunity_id}
    )
    assert analyze_resp.status_code == 202, analyze_resp.text
    analysis_id = analyze_resp.json()["id"]
    assert analyze_resp.json()["status"] == "pending"

    from cios.tasks.competitive_intel import _run_async

    result = await _run_async(tenant_id, opportunity_id, analysis_id)
    assert result["status"] == "completed", result

    fetched = await client.get(f"/api/v1/competitors/analyze/{analysis_id}", headers=headers)
    assert fetched.status_code == 200, fetched.text
    body = fetched.json()

    assert body["status"] == "completed"
    assert body["solicitation_id"] == seeded["solicitation_id"]
    assert body["candidate_pool_size"] == 2  # excludes self

    front_runner = body["front_runner"]
    assert front_runner["contractor_id"] == seeded["front_runner_contractor_id"]
    assert front_runner["rank"] == 1
    assert front_runner["competitor_id"] == seeded["tracked_competitor_id"]
    assert front_runner["threat_level"] == "high"
    assert front_runner["pricing_tendency"] == "aggressive"
    assert front_runner["known_strengths"] == ["Incumbent relationships"]

    assert len(body["next_tiers"]) == 1
    next_tier = body["next_tiers"][0]
    assert next_tier["contractor_id"] == seeded["second_tier_contractor_id"]
    assert next_tier["rank"] == 2
    # No pre-existing Competitor for this one — the task must auto-create
    # and link one rather than leaving it unenriched.
    assert next_tier["competitor_id"] is not None

    latest = await client.get(
        f"/api/v1/competitors/analyze/by-opportunity/{opportunity_id}", headers=headers
    )
    assert latest.status_code == 200
    assert latest.json()["id"] == analysis_id

    async with async_session_factory() as db:
        await _set_tenant(db, tenant_id)
        linked_contractor = await db.get(
            WPHContractor, uuid.UUID(seeded["second_tier_contractor_id"])
        )
        assert linked_contractor.competitor_id is not None
        auto_created = await db.get(Competitor, linked_contractor.competitor_id)
        assert auto_created.company_name == "Second Tier Inc"


@pytest.mark.anyio
async def test_analyze_fails_loudly_when_no_wph_solicitation_exists_yet(client: AsyncClient):
    headers, tenant_id = await _register(client)

    opp_resp = await client.post(
        "/api/v1/opportunities",
        headers=headers,
        json={"title": "No WPH Yet Opp", "agency": "Test Agency"},
    )
    opportunity_id = opp_resp.json()["id"]

    analyze_resp = await client.post(
        "/api/v1/competitors/analyze", headers=headers, json={"opportunity_id": opportunity_id}
    )
    analysis_id = analyze_resp.json()["id"]

    from cios.tasks.competitive_intel import _run_async

    result = await _run_async(tenant_id, opportunity_id, analysis_id)
    assert result["status"] == "failed"
    assert "Winning Profile" in result["error"]

    fetched = await client.get(f"/api/v1/competitors/analyze/{analysis_id}", headers=headers)
    assert fetched.json()["status"] == "failed"
    assert fetched.json()["error_message"]
