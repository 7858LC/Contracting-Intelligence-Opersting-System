"""Tenant document object storage — S3-compatible (AWS S3, R2, MinIO, etc.).

Knowledge Vault's upload endpoint used to read a file into memory, pass the
raw bytes straight through as a Celery task argument (through Redis, the
broker — a real problem on its own at the endpoint's 50MB ceiling), extract
text from them, and then discard them. Nothing about the original document
survived ingestion: KnowledgeDocument.s3_key (cios/models/knowledge_vault.py)
has existed on the table the whole time but no code ever wrote to it, and
config.py/​.env.example have carried s3_endpoint/s3_bucket_documents/etc.
unused since before this file existed. This module is what actually uses
them: the endpoint uploads the original file here first and gets back a key,
the ingestion task downloads by that key instead of receiving bytes inline,
and the key is what lets a tenant retrieve their own document afterward.

aiobotocore (already a declared dependency, previously unused — same as
boto3) gives a native async client; no thread-pool wrapping needed.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from aiobotocore.session import get_session

from cios.config import settings


def build_storage_key(tenant_id: str, document_id: str, file_name: str | None) -> str:
    """Tenant-prefixed key — same per-tenant isolation reasoning as
    TenantVectorStore's collection naming: never let one tenant's key range
    overlap another's, so a bucket-level access mistake can't leak across
    tenants the way a shared prefix could."""
    safe_name = (file_name or "document").replace("/", "_")
    return f"{tenant_id}/{document_id}/{safe_name}"


class DocumentStorage:
    """Thin async wrapper over the Knowledge Vault source-document bucket
    (settings.s3_bucket_documents)."""

    def __init__(self) -> None:
        self._bucket = settings.s3_bucket_documents

    @asynccontextmanager
    async def _client(self) -> AsyncIterator[Any]:
        session = get_session()
        async with session.create_client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key_id or None,
            aws_secret_access_key=settings.s3_secret_access_key or None,
            region_name=settings.s3_region,
        ) as client:
            yield client

    async def upload(self, key: str, content: bytes, content_type: str) -> None:
        async with self._client() as client:
            await client.put_object(
                Bucket=self._bucket, Key=key, Body=content, ContentType=content_type
            )

    async def download(self, key: str) -> bytes:
        async with self._client() as client:
            resp = await client.get_object(Bucket=self._bucket, Key=key)
            return await resp["Body"].read()

    async def delete(self, key: str) -> None:
        async with self._client() as client:
            await client.delete_object(Bucket=self._bucket, Key=key)

    async def presigned_download_url(self, key: str, *, expires_in: int = 300) -> str:
        async with self._client() as client:
            return await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires_in,
            )
