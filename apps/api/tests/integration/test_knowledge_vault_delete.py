"""Regression test for DELETE /api/v1/knowledge-vault/{document_id}.

Before this fix, a Qdrant failure (unreachable, timeout, misconfigured
client) on the vector-cleanup step raised straight out of the endpoint,
so the Postgres delete below it never ran and the whole request failed —
even though nothing about the user's own document row was actually broken.
Reported live as the delete button on the Knowledge Vault page always
showing "Delete failed" for a vectorized document.
"""

from __future__ import annotations

import random
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from cios.core.database import async_session_factory
from cios.models.knowledge_vault import KnowledgeDocument


def _fake_client_ip() -> str:
    return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


async def _register(client: AsyncClient) -> dict:
    suffix = uuid.uuid4().hex[:10]
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"kv-delete-{suffix}@example.com",
            "password": "SmokeTest123!",
            "full_name": "KV Delete Test",
            "company_name": f"KV Delete Co {suffix}",
        },
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_vectorized_document(tenant_id: str) -> str:
    """Insert a KnowledgeDocument as if ingestion had already vectorized it
    (qdrant_collection set) — this is the state that triggers the Qdrant
    delete call the bug is in."""
    async with async_session_factory() as db:
        from sqlalchemy import text

        await db.execute(
            text("SELECT set_config('app.current_tenant', :t, false)"),
            {"t": tenant_id},
        )
        doc = KnowledgeDocument(
            tenant_id=uuid.UUID(tenant_id),
            title="Test Document",
            document_type="general",
            uploaded_by=uuid.uuid4(),
            vectorization_status="completed",
            is_vectorized=True,
            qdrant_collection=f"cios_tenant_{tenant_id.replace('-', '_')}",
        )
        db.add(doc)
        await db.commit()
        return str(doc.id)


@pytest.mark.anyio
async def test_delete_succeeds_even_when_qdrant_delete_fails(client: AsyncClient):
    headers = await _register(client)
    me = await client.get("/api/v1/auth/me", headers=headers)
    tenant_id = me.json()["tenant_id"]

    doc_id = await _create_vectorized_document(tenant_id)

    with patch(
        "cios.vector.tenant_store.TenantVectorStore.delete_document",
        new=AsyncMock(side_effect=RuntimeError("Qdrant unreachable")),
    ):
        resp = await client.delete(f"/api/v1/knowledge-vault/{doc_id}", headers=headers)

    assert resp.status_code == 204, resp.text

    async with async_session_factory() as db:
        from sqlalchemy import text

        await db.execute(
            text("SELECT set_config('app.current_tenant', :t, false)"), {"t": tenant_id}
        )
        row = (
            await db.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.id == uuid.UUID(doc_id))
            )
        ).scalar_one_or_none()
        assert row is None


@pytest.mark.anyio
async def test_delete_removes_document_when_qdrant_delete_succeeds(client: AsyncClient):
    headers = await _register(client)
    me = await client.get("/api/v1/auth/me", headers=headers)
    tenant_id = me.json()["tenant_id"]

    doc_id = await _create_vectorized_document(tenant_id)

    with patch(
        "cios.vector.tenant_store.TenantVectorStore.delete_document",
        new=AsyncMock(return_value=None),
    ) as mock_delete:
        resp = await client.delete(f"/api/v1/knowledge-vault/{doc_id}", headers=headers)

    assert resp.status_code == 204, resp.text
    mock_delete.assert_awaited_once_with(doc_id)


@pytest.mark.anyio
async def test_delete_unknown_document_returns_404(client: AsyncClient):
    headers = await _register(client)
    resp = await client.delete(f"/api/v1/knowledge-vault/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 404
