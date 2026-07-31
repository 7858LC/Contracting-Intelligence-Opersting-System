"""DELETE /bid-decisions/{id} — soft-delete (is_archived), same recoverability
pattern as Opportunity's archive endpoint. Added alongside the frontend
delete+confirm UI to declutter accumulated test/demo decisions without
depending on a database backup/restore for a mistaken delete."""

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
            "email": f"bd-delete-{suffix}@example.com",
            "password": "BdDeleteTest123!",
            "full_name": "Bid Decision Delete Test",
            "company_name": f"Bd Delete Co {suffix}",
        },
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.mark.anyio
async def test_delete_bid_decision_removes_it_from_the_list(client: AsyncClient):
    headers = await _register(client)

    create_opp = await client.post(
        "/api/v1/opportunities",
        headers=headers,
        json={"title": "Delete Test Opportunity", "agency": "Test Agency"},
    )
    assert create_opp.status_code == 201, create_opp.text
    opp_id = create_opp.json()["id"]

    create_decision = await client.post(
        "/api/v1/bid-decisions", headers=headers, json={"opportunity_id": opp_id}
    )
    assert create_decision.status_code == 202, create_decision.text
    decision_id = create_decision.json()["decision_id"]

    before = await client.get("/api/v1/bid-decisions", headers=headers)
    assert any(item["id"] == decision_id for item in before.json()["items"])

    delete = await client.delete(f"/api/v1/bid-decisions/{decision_id}", headers=headers)
    assert delete.status_code == 204, delete.text

    after = await client.get("/api/v1/bid-decisions", headers=headers)
    assert not any(item["id"] == decision_id for item in after.json()["items"])


@pytest.mark.anyio
async def test_delete_bid_decision_is_tenant_scoped(client: AsyncClient):
    a_headers = await _register(client)
    b_headers = await _register(client)

    create_opp = await client.post(
        "/api/v1/opportunities",
        headers=a_headers,
        json={"title": "Tenant A Delete Scope Test", "agency": "Test Agency"},
    )
    assert create_opp.status_code == 201, create_opp.text
    opp_id = create_opp.json()["id"]

    create_decision = await client.post(
        "/api/v1/bid-decisions", headers=a_headers, json={"opportunity_id": opp_id}
    )
    assert create_decision.status_code == 202, create_decision.text
    decision_id = create_decision.json()["decision_id"]

    cross_delete = await client.delete(f"/api/v1/bid-decisions/{decision_id}", headers=b_headers)
    assert cross_delete.status_code == 404, cross_delete.text

    still_there = await client.get("/api/v1/bid-decisions", headers=a_headers)
    assert any(item["id"] == decision_id for item in still_there.json()["items"])
