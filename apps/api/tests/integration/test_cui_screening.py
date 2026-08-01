"""Proves the CUI/classification restriction actually works end to end:
upload-time attestation is required, and a document whose extracted text
carries a common CUI/classification banner marking gets blocked before
vectorization instead of silently entering the tenant's searchable
Knowledge Vault. See cios/core/cui_screening.py and
docs/legal/cui-restriction-draft.md for the reasoning.

Ingestion (cios/tasks/ingestion.py's _ingest_async) is a Celery task body —
there's no worker running in this test tier, so `.delay()` only enqueues to
Redis without executing (same reasoning as test_opportunity_analysis_pipeline.py
etc.: call the underlying `_async` coroutine directly). TenantVectorStore is
mocked for the clean-content path since Qdrant isn't part of this test
tier's real backing services (only Postgres/Redis/moto-S3 are, see
conftest.py) — same pattern as test_knowledge_vault_delete.py.
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
from cios.models.tenant import AuditLog


def _fake_client_ip() -> str:
    return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


async def _register(client: AsyncClient) -> tuple[dict, str]:
    suffix = uuid.uuid4().hex[:10]
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"cui-{suffix}@example.com",
            "password": "SmokeTest123!",
            "full_name": "CUI Screening Test",
            "company_name": f"CUI Screening Co {suffix}",
        },
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert resp.status_code == 201, resp.text
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    me = await client.get("/api/v1/auth/me", headers=headers)
    return headers, me.json()["tenant_id"]


async def _get_document_row(tenant_id: str, document_id: str) -> KnowledgeDocument:
    async with async_session_factory() as db:
        from sqlalchemy import text

        await db.execute(
            text("SELECT set_config('app.current_tenant', :t, false)"), {"t": tenant_id}
        )
        row = (
            await db.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.id == uuid.UUID(document_id))
            )
        ).scalar_one_or_none()
        assert row is not None
        return row


@pytest.mark.anyio
async def test_upload_without_attestation_field_is_rejected(client: AsyncClient):
    headers, _ = await _register(client)
    resp = await client.post(
        "/api/v1/knowledge-vault/upload",
        headers=headers,
        files={"file": ("doc.txt", b"ordinary business content", "text/plain")},
        data={"document_type": "general"},
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.anyio
async def test_upload_with_attestation_false_is_rejected(client: AsyncClient):
    headers, _ = await _register(client)
    resp = await client.post(
        "/api/v1/knowledge-vault/upload",
        headers=headers,
        files={"file": ("doc.txt", b"ordinary business content", "text/plain")},
        data={"document_type": "general", "attestation": "false"},
    )
    assert resp.status_code == 422, resp.text
    assert "CUI" in resp.json()["detail"]


@pytest.mark.anyio
async def test_upload_honors_attested_document_type(client: AsyncClient):
    """Regression: document_type/title/description/tags were previously
    plain `str` params, which FastAPI silently reads as unused Query
    parameters once a File() sibling is present — the multipart form
    fields the frontend sends were discarded and every upload fell back to
    "general" regardless of the UI's selection. Form(...) fixes this; this
    test would have failed against the old code (doc_type always "general")."""
    headers, tenant_id = await _register(client)
    resp = await client.post(
        "/api/v1/knowledge-vault/upload",
        headers=headers,
        files={"file": ("rfp.txt", b"ordinary business content", "text/plain")},
        data={"document_type": "solicitation", "attestation": "true"},
    )
    assert resp.status_code == 202, resp.text
    doc = await _get_document_row(tenant_id, resp.json()["document_id"])
    assert doc.document_type == "solicitation"


@pytest.mark.anyio
async def test_upload_records_attestation_audit_log(client: AsyncClient):
    headers, tenant_id = await _register(client)
    resp = await client.post(
        "/api/v1/knowledge-vault/upload",
        headers=headers,
        files={"file": ("doc.txt", b"ordinary business content", "text/plain")},
        data={"document_type": "general", "attestation": "true"},
    )
    assert resp.status_code == 202, resp.text
    document_id = resp.json()["document_id"]

    async with async_session_factory() as db:
        from sqlalchemy import text

        await db.execute(
            text("SELECT set_config('app.current_tenant', :t, false)"), {"t": tenant_id}
        )
        row = (
            await db.execute(
                select(AuditLog).where(
                    AuditLog.action == "knowledge_vault_upload_attested",
                    AuditLog.resource_id == document_id,
                )
            )
        ).scalar_one_or_none()
        assert row is not None
        assert row.extra_metadata == {"attestation_confirmed": True}


@pytest.mark.anyio
async def test_ingestion_blocks_document_with_cui_marking(client: AsyncClient):
    from cios.tasks.ingestion import _ingest_async

    headers, tenant_id = await _register(client)
    marked_content = (
        b"CONTROLLED UNCLASSIFIED INFORMATION\n\n"
        b"This technical data package describes the widget assembly."
    )
    upload = await client.post(
        "/api/v1/knowledge-vault/upload",
        headers=headers,
        files={"file": ("marked.txt", marked_content, "text/plain")},
        data={"document_type": "general", "attestation": "true"},
    )
    assert upload.status_code == 202, upload.text
    document_id = upload.json()["document_id"]

    doc_before = await _get_document_row(tenant_id, document_id)
    result = await _ingest_async(tenant_id, document_id, doc_before.s3_key, "text/plain")

    assert result["status"] == "blocked_cui"
    assert "CONTROLLED_UNCLASSIFIED_INFORMATION" in result["matches"]

    doc = await _get_document_row(tenant_id, document_id)
    assert doc.vectorization_status == "blocked_cui"
    assert doc.is_vectorized is False
    assert doc.chunk_count == 0
    assert doc.extracted_text is None
    assert "CONTROLLED_UNCLASSIFIED_INFORMATION" in doc.extra_metadata["cui_screen_matches"]

    # The object must not remain in storage once it's known to be blocked.
    from botocore.exceptions import ClientError

    from cios.core.storage import DocumentStorage

    with pytest.raises(ClientError) as exc_info:
        await DocumentStorage().download(doc.s3_key)
    assert exc_info.value.response["Error"]["Code"] == "NoSuchKey"

    async with async_session_factory() as db:
        from sqlalchemy import text

        await db.execute(
            text("SELECT set_config('app.current_tenant', :t, false)"), {"t": tenant_id}
        )
        audit_row = (
            await db.execute(
                select(AuditLog).where(
                    AuditLog.action == "knowledge_vault_upload_blocked_cui_marking",
                    AuditLog.resource_id == document_id,
                )
            )
        ).scalar_one_or_none()
        assert audit_row is not None


@pytest.mark.anyio
async def test_ingestion_vectorizes_clean_document_normally(client: AsyncClient):
    from cios.tasks.ingestion import _ingest_async

    headers, tenant_id = await _register(client)
    upload = await client.post(
        "/api/v1/knowledge-vault/upload",
        headers=headers,
        files={"file": ("clean.txt", b"Ordinary past performance narrative.", "text/plain")},
        data={"document_type": "past_performance", "attestation": "true"},
    )
    assert upload.status_code == 202, upload.text
    document_id = upload.json()["document_id"]
    doc_before = await _get_document_row(tenant_id, document_id)

    with (
        patch(
            "cios.vector.tenant_store.TenantVectorStore.ensure_collection",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "cios.vector.tenant_store.TenantVectorStore._embed",
            new=AsyncMock(return_value=[0.0] * 8),
        ),
        patch(
            "cios.vector.tenant_store.TenantVectorStore.upsert",
            new=AsyncMock(return_value="fake-point-id"),
        ),
    ):
        result = await _ingest_async(tenant_id, document_id, doc_before.s3_key, "text/plain")

    assert result["chunks"] == 1
    doc = await _get_document_row(tenant_id, document_id)
    assert doc.vectorization_status == "completed"
    assert doc.is_vectorized is True
    assert doc.chunk_count == 1
