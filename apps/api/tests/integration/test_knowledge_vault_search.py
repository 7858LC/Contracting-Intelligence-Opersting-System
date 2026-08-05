"""Knowledge Vault search must not 500 for a tenant with zero documents.

Regression test for the TenantVectorStore.search() bug: it queried Qdrant
directly without first calling ensure_collection() (upsert() already did).
A tenant who's never uploaded anything has no Qdrant collection yet, so
their first search hit an unhandled 404 from Qdrant — see
cios/vector/tenant_store.py. This hits the real POST /knowledge-vault/search
endpoint against the real Qdrant service (ci.yml's api-test job), the same
"hit something real" bar as Postgres/Redis/S3 elsewhere in this directory.

The embedding call itself is monkeypatched — Voyage AI is a real paid
external API with no CI credential configured for it, unlike Postgres/
Redis/Qdrant/S3 which are all real services this suite talks to directly.
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
            "email": f"kv-search-{suffix}@example.com",
            "password": "SmokeTest123!",
            "full_name": "KV Search Test",
            "company_name": f"KV Search Co {suffix}",
        },
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _fake_embed(self: object, text: str) -> list[float]:
    from cios.vector.tenant_store import EMBEDDING_DIM

    return [0.0] * EMBEDDING_DIM


@pytest.mark.anyio
async def test_search_returns_empty_results_for_tenant_with_no_documents(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    """The exact scenario that 500'd in production: a freshly registered
    tenant who has never uploaded a document searches the Knowledge Vault.
    Their Qdrant collection doesn't exist yet — this must return an empty
    result set, not a 500."""
    monkeypatch.setattr("cios.vector.tenant_store.TenantVectorStore._embed", _fake_embed)
    headers = await _register(client)

    resp = await client.post(
        "/api/v1/knowledge-vault/search",
        headers=headers,
        json={"query": "anything"},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["results"] == []
    assert body["count"] == 0
    assert body["query"] == "anything"


@pytest.mark.anyio
async def test_search_is_repeatable_once_the_collection_exists(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    """A second search from the same tenant (collection now created by the
    first call) must still succeed — proves ensure_collection()'s
    already-exists branch works against the real service, not just the
    create branch covered above."""
    monkeypatch.setattr("cios.vector.tenant_store.TenantVectorStore._embed", _fake_embed)
    headers = await _register(client)

    first = await client.post(
        "/api/v1/knowledge-vault/search", headers=headers, json={"query": "first"}
    )
    assert first.status_code == 200, first.text

    second = await client.post(
        "/api/v1/knowledge-vault/search", headers=headers, json={"query": "second"}
    )
    assert second.status_code == 200, second.text
    assert second.json()["results"] == []
