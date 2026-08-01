"""End-to-end proof for the Capability Gap Analysis pipeline (Module 5/15):
turning an already-computed WPHAlignment.gaps + .gap_closures for the
tenant's own ("self") contractor into persisted CapabilityGap rows.

Covers:
1. run_capability_gap_analysis translates each WPH gap into a CapabilityGap
   row with severity/category/description carried over and the matching
   gap_closure's recommendation/timeline/cost_band attached.
2. Re-running for the same opportunity supersedes the previous run's gaps
   rather than accumulating duplicates.
3. The task fails loudly (not silently) when Winning Profile hasn't been
   run yet for the opportunity, instead of completing with nothing.
"""

from __future__ import annotations

import random
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from cios.core.database import async_session_factory
from cios.models.winning_profile import WPHAlignment, WPHContractor, WPHProfile, WPHSolicitation


def _fake_client_ip() -> str:
    return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


_GAP_ANALYSIS_PASSWORD = "GapAnalysisTest123!"


async def _register(client: AsyncClient) -> tuple[dict, str]:
    """Capabilities & Gap Analysis is gated Growth+ via
    require_feature() (api/v1/router.py) — register always issues
    plan="trial", so this bumps the tenant's plan and logs in again for a
    token that actually carries it (see conftest's upgrade_tenant_plan)."""
    from tests.integration.conftest import upgrade_tenant_plan

    suffix = uuid.uuid4().hex[:10]
    email = f"cga-{suffix}@example.com"
    ip_header = {"X-Forwarded-For": _fake_client_ip()}
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": _GAP_ANALYSIS_PASSWORD,
            "full_name": "Gap Analysis Test",
            "company_name": f"Gap Analysis Co {suffix}",
        },
        headers=ip_header,
    )
    assert resp.status_code == 201, resp.text
    tenant_id = resp.json()["tenant_id"]
    await upgrade_tenant_plan(tenant_id)

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": _GAP_ANALYSIS_PASSWORD},
        headers=ip_header,
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, tenant_id


async def _set_tenant(db, tenant_id: str) -> None:
    await db.execute(
        text("SELECT set_config('app.current_tenant', :t, false)"), {"t": tenant_id}
    )


_GAPS = [
    {
        "attribute_key": "security_clearance",
        "attribute_name": "Facility Security Clearance",
        "category": "security",
        "severity": "critical",
        "importance_weight": 20.0,
        "required_level": 90.0,
        "contractor_level": 20.0,
        "gap_size": 70.0,
        "impact": "Shortfall of 70 points on a 20/100 importance attribute — critical exposure.",
    },
    {
        "attribute_key": "past_performance_scale",
        "attribute_name": "Past Performance at Scale",
        "category": "past_performance",
        "severity": "moderate",
        "importance_weight": 10.0,
        "required_level": 80.0,
        "contractor_level": 55.0,
        "gap_size": 25.0,
        "impact": "Shortfall of 25 points on a 10/100 importance attribute — moderate exposure.",
    },
]

_GAP_CLOSURES = [
    {
        "gap_attribute_key": "security_clearance",
        "gap_attribute_name": "Facility Security Clearance",
        "recommendation": "[CRITICAL] Facility Security Clearance: Team with a cleared partner. "
        "Target lift 20 → 71/100.",
        "action_type": "partner",
        "effort": "high",
        "timeline_months": 14,
        "feasibility": "medium",
        "cost_band": "$$$",
        "closes_gap_to": 71.0,
    },
    {
        "gap_attribute_key": "past_performance_scale",
        "gap_attribute_name": "Past Performance at Scale",
        "recommendation": "[MODERATE] Past Performance at Scale: Add a teaming partner with "
        "directly relevant CPARS. Target lift 55 → 73/100.",
        "action_type": "teaming",
        "effort": "low",
        "timeline_months": 1,
        "feasibility": "high",
        "cost_band": "$",
        "closes_gap_to": 73.0,
    },
]


async def _seed_solicitation_profile_and_self_alignment(
    tenant_id: str, opportunity_id: str, *, gaps: list | None = None
) -> dict:
    """Directly construct a minimal WPH pipeline state — solicitation, a
    current profile, a self contractor, and its alignment carrying
    pre-computed gaps/gap_closures — bypassing the full extraction/scoring
    pipeline (deterministic but not the thing under test here)."""
    async with async_session_factory() as db:
        await _set_tenant(db, tenant_id)

        sol = WPHSolicitation(
            tenant_id=uuid.UUID(tenant_id),
            opportunity_id=uuid.UUID(opportunity_id),
            title="Gap Analysis Test Solicitation",
            agency="Test Agency",
        )
        db.add(sol)
        await db.flush()

        profile = WPHProfile(
            tenant_id=uuid.UUID(tenant_id),
            solicitation_id=sol.id,
            version=1,
            is_current=True,
            overall_confidence=80.0,
            model_used="claude-sonnet-4-6",
        )
        db.add(profile)
        await db.flush()

        self_contractor = WPHContractor(
            tenant_id=uuid.UUID(tenant_id), name="Our Own Org", is_self=True
        )
        db.add(self_contractor)
        await db.flush()

        alignment = WPHAlignment(
            tenant_id=uuid.UUID(tenant_id),
            solicitation_id=sol.id,
            profile_id=profile.id,
            contractor_id=self_contractor.id,
            contractor_name=self_contractor.name,
            overall_alignment_score=55.0,
            rank=1,
            gaps=gaps if gaps is not None else _GAPS,
            gap_closures=_GAP_CLOSURES if gaps is None or gaps else [],
        )
        db.add(alignment)
        await db.commit()

        return {
            "solicitation_id": str(sol.id),
            "profile_id": str(profile.id),
            "self_contractor_id": str(self_contractor.id),
        }


@pytest.mark.anyio
async def test_analyze_gaps_translates_wph_gaps_into_capability_gap_rows(client: AsyncClient):
    headers, tenant_id = await _register(client)

    opp_resp = await client.post(
        "/api/v1/opportunities",
        headers=headers,
        json={"title": "Gap Analysis Test Opp", "agency": "Test Agency"},
    )
    assert opp_resp.status_code == 201, opp_resp.text
    opportunity_id = opp_resp.json()["id"]

    seeded = await _seed_solicitation_profile_and_self_alignment(tenant_id, opportunity_id)

    analyze_resp = await client.post(
        "/api/v1/capabilities/analyze-gaps",
        headers=headers,
        json={"opportunity_id": opportunity_id},
    )
    assert analyze_resp.status_code == 201, analyze_resp.text
    run_id = analyze_resp.json()["id"]
    assert analyze_resp.json()["status"] == "pending"

    from cios.tasks.gap_analysis import _run_async

    result = await _run_async(tenant_id, opportunity_id, run_id)
    assert result["status"] == "completed", result
    assert result["gap_count"] == 2

    fetched_run = await client.get(f"/api/v1/capabilities/gaps/analyze/{run_id}", headers=headers)
    assert fetched_run.status_code == 200, fetched_run.text
    run_body = fetched_run.json()
    assert run_body["status"] == "completed"
    assert run_body["solicitation_id"] == seeded["solicitation_id"]
    assert run_body["gap_count"] == 2

    latest_run = await client.get(
        f"/api/v1/capabilities/gaps/analyze/by-opportunity/{opportunity_id}", headers=headers
    )
    assert latest_run.status_code == 200
    assert latest_run.json()["id"] == run_id

    gaps_resp = await client.get(
        "/api/v1/capabilities/gaps", headers=headers, params={"opportunity_id": opportunity_id}
    )
    assert gaps_resp.status_code == 200, gaps_resp.text
    gaps = gaps_resp.json()["gaps"]
    assert len(gaps) == 2

    critical = next(g for g in gaps if g["severity"] == "critical")
    assert critical["gap_name"] == "Facility Security Clearance"
    assert critical["category"] == "security"
    assert critical["analysis_run_id"] == run_id
    assert critical["teaming_recommendation"] is not None  # action_type == "partner"
    assert critical["remediation_options"][0]["action_type"] == "partner"
    assert critical["estimated_time_to_close_days"] == 14 * 30
    assert critical["estimated_cost_to_close"] == 150_000.0  # $$$ band
    assert critical["evidence"]["gap_size"] == 70.0
    assert critical["confidence_score"] == 0.8

    moderate = next(g for g in gaps if g["severity"] == "moderate")
    assert moderate["gap_name"] == "Past Performance at Scale"
    assert moderate["teaming_recommendation"] is not None  # action_type == "teaming"
    assert moderate["estimated_cost_to_close"] == 15_000.0  # $ band


@pytest.mark.anyio
async def test_analyze_gaps_rerun_supersedes_prior_run(client: AsyncClient):
    headers, tenant_id = await _register(client)

    opp_resp = await client.post(
        "/api/v1/opportunities",
        headers=headers,
        json={"title": "Gap Analysis Rerun Opp", "agency": "Test Agency"},
    )
    opportunity_id = opp_resp.json()["id"]

    seeded = await _seed_solicitation_profile_and_self_alignment(
        tenant_id, opportunity_id, gaps=_GAPS[:1]
    )

    from cios.tasks.gap_analysis import _run_async

    first = await client.post(
        "/api/v1/capabilities/analyze-gaps",
        headers=headers,
        json={"opportunity_id": opportunity_id},
    )
    await _run_async(tenant_id, opportunity_id, first.json()["id"])

    # Simulate re-scoring surfacing an additional gap on the *same*
    # alignment row (a real rerun doesn't create a new WPH solicitation —
    # it recomputes the existing one) and re-run — the previous run's gap
    # rows must not linger alongside the new set.
    async with async_session_factory() as db:
        await _set_tenant(db, tenant_id)
        alignment = (
            await db.execute(
                text(
                    "SELECT id FROM wph_alignments WHERE profile_id = :profile_id"
                ),
                {"profile_id": seeded["profile_id"]},
            )
        ).scalar_one()
        row = await db.get(WPHAlignment, alignment)
        row.gaps = _GAPS
        row.gap_closures = _GAP_CLOSURES
        await db.commit()

    second = await client.post(
        "/api/v1/capabilities/analyze-gaps",
        headers=headers,
        json={"opportunity_id": opportunity_id},
    )
    result = await _run_async(tenant_id, opportunity_id, second.json()["id"])
    assert result["gap_count"] == 2

    gaps_resp = await client.get(
        "/api/v1/capabilities/gaps", headers=headers, params={"opportunity_id": opportunity_id}
    )
    gaps = gaps_resp.json()["gaps"]
    assert len(gaps) == 2
    assert all(g["analysis_run_id"] == second.json()["id"] for g in gaps)


@pytest.mark.anyio
async def test_analyze_gaps_fails_loudly_when_no_wph_solicitation_exists_yet(client: AsyncClient):
    headers, tenant_id = await _register(client)

    opp_resp = await client.post(
        "/api/v1/opportunities",
        headers=headers,
        json={"title": "No WPH Yet Opp", "agency": "Test Agency"},
    )
    opportunity_id = opp_resp.json()["id"]

    analyze_resp = await client.post(
        "/api/v1/capabilities/analyze-gaps",
        headers=headers,
        json={"opportunity_id": opportunity_id},
    )
    run_id = analyze_resp.json()["id"]

    from cios.tasks.gap_analysis import _run_async

    result = await _run_async(tenant_id, opportunity_id, run_id)
    assert result["status"] == "failed"
    assert "Winning Profile" in result["error"]

    fetched = await client.get(f"/api/v1/capabilities/gaps/analyze/{run_id}", headers=headers)
    assert fetched.json()["status"] == "failed"
    assert fetched.json()["error_message"]
