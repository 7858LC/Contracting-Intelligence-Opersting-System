"""Proves Knowledge Vault documents actually survive ingestion.

Before this fix, POST /knowledge-vault/upload read the file into memory,
passed the raw bytes straight through as a Celery task argument, and the
ingestion task discarded them after text extraction — nothing about the
original document was ever persisted anywhere, and there was no way for a
tenant to retrieve what they'd uploaded. cios/core/storage.py fixes that;
these tests hit the real (moto-backed, see conftest.py's
_knowledge_vault_object_storage fixture) S3-compatible endpoint end to end.
"""

from __future__ import annotations

import random
import uuid

import boto3
import pytest
from httpx import AsyncClient

from cios.config import settings


def _fake_client_ip() -> str:
    return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


async def _register(client: AsyncClient) -> dict:
    suffix = uuid.uuid4().hex[:10]
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"kv-storage-{suffix}@example.com",
            "password": "SmokeTest123!",
            "full_name": "KV Storage Test",
            "company_name": f"KV Storage Co {suffix}",
        },
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        region_name=settings.s3_region,
    )


@pytest.mark.anyio
async def test_upload_persists_original_file_to_object_storage(client: AsyncClient):
    headers = await _register(client)
    original_bytes = b"This is the original RFP text that must survive ingestion."

    resp = await client.post(
        "/api/v1/knowledge-vault/upload",
        headers=headers,
        files={"file": ("rfp.txt", original_bytes, "text/plain")},
        data={"document_type": "solicitation", "attestation": "true"},
    )
    assert resp.status_code == 202, resp.text
    document_id = resp.json()["document_id"]

    list_resp = await client.get("/api/v1/knowledge-vault", headers=headers)
    doc_row = next(d for d in list_resp.json()["items"] if d["id"] == document_id)
    assert doc_row["file_name"] == "rfp.txt"

    # The object actually exists in the bucket under a tenant-prefixed key —
    # not just a row saying it does.
    me = await client.get("/api/v1/auth/me", headers=headers)
    tenant_id = me.json()["tenant_id"]
    key = f"{tenant_id}/{document_id}/rfp.txt"
    stored = _s3_client().get_object(Bucket=settings.s3_bucket_documents, Key=key)
    assert stored["Body"].read() == original_bytes


@pytest.mark.anyio
async def test_download_url_returns_the_original_bytes(client: AsyncClient):
    headers = await _register(client)
    original_bytes = b"Capability statement content for download-roundtrip test."

    upload = await client.post(
        "/api/v1/knowledge-vault/upload",
        headers=headers,
        files={"file": ("capstmt.txt", original_bytes, "text/plain")},
        data={"document_type": "capability_statement", "attestation": "true"},
    )
    assert upload.status_code == 202, upload.text
    document_id = upload.json()["document_id"]

    download = await client.get(
        f"/api/v1/knowledge-vault/{document_id}/download", headers=headers
    )
    assert download.status_code == 200, download.text
    body = download.json()
    assert body["expires_in"] > 0
    assert "download_url" in body

    async with AsyncClient() as raw_http:
        fetched = await raw_http.get(body["download_url"])
    assert fetched.status_code == 200
    assert fetched.content == original_bytes


@pytest.mark.anyio
async def test_download_url_is_tenant_scoped(client: AsyncClient):
    owner_headers = await _register(client)
    other_headers = await _register(client)

    upload = await client.post(
        "/api/v1/knowledge-vault/upload",
        headers=owner_headers,
        files={"file": ("private.txt", b"secret", "text/plain")},
        data={"document_type": "general", "attestation": "true"},
    )
    document_id = upload.json()["document_id"]

    blocked = await client.get(
        f"/api/v1/knowledge-vault/{document_id}/download", headers=other_headers
    )
    assert blocked.status_code == 404, blocked.text


@pytest.mark.anyio
async def test_delete_removes_the_object_from_storage(client: AsyncClient):
    headers = await _register(client)
    upload = await client.post(
        "/api/v1/knowledge-vault/upload",
        headers=headers,
        files={"file": ("temp.txt", b"delete me", "text/plain")},
        data={"document_type": "general", "attestation": "true"},
    )
    document_id = upload.json()["document_id"]
    me = await client.get("/api/v1/auth/me", headers=headers)
    tenant_id = me.json()["tenant_id"]
    key = f"{tenant_id}/{document_id}/temp.txt"

    # Confirms the object is really there before delete, so the assertion
    # after delete proves removal rather than the object never existing.
    _s3_client().get_object(Bucket=settings.s3_bucket_documents, Key=key)

    resp = await client.delete(f"/api/v1/knowledge-vault/{document_id}", headers=headers)
    assert resp.status_code == 204, resp.text

    from botocore.exceptions import ClientError

    with pytest.raises(ClientError) as exc_info:
        _s3_client().get_object(Bucket=settings.s3_bucket_documents, Key=key)
    assert exc_info.value.response["Error"]["Code"] == "NoSuchKey"
