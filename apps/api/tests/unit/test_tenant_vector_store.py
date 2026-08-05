"""TenantVectorStore.search() must create the tenant's Qdrant collection
before querying it, and must call methods that actually exist on the
installed qdrant-client.

Regression test for two compounding bugs:

1. search() (unlike upsert()) never called ensure_collection(). A tenant
   who had never uploaded a document — so their collection was never
   created — got an unhandled 404 from Qdrant on their first search.
2. search() called `AsyncQdrantClient.search()`, which was removed in
   favor of `query_points()` around qdrant-client 1.10-1.11 (see its
   changelog). This project pins only a floor
   ("qdrant-client>=1.11.0", no ceiling, no lockfile), so search() failed
   with AttributeError on *every* call, for *every* tenant, independent
   of bug #1.

Either exception is a raw, non-HTTPException error that escapes FastAPI's
ExceptionMiddleware (which sits inside CORSMiddleware) and is caught
instead by the outer ServerErrorMiddleware, whose 500 response never
passes back through CORSMiddleware's header-adding logic — so the browser
reports it as a CORS failure rather than the real 500.

These mocks use create_autospec(AsyncQdrantClient) rather than a bare
MagicMock specifically so that mocking a method name that doesn't exist on
the real client (like the old `client.search`) raises immediately, the way
a bare MagicMock never would — a bare-MagicMock version of this test
passed happily against the removed-method bug.
"""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://cios_user:cios_pass@localhost/x")
os.environ.setdefault("JWT_SECRET", "test_secret_minimum_32_characters_long")
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)
os.environ.setdefault("ANTHROPIC_API_KEY", "test_key")

from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

from qdrant_client import AsyncQdrantClient

from cios.vector.tenant_store import EMBEDDING_DIM, TenantVectorStore


def _autospec_client() -> MagicMock:
    client = create_autospec(AsyncQdrantClient, instance=True)
    client.get_collections = AsyncMock()
    client.create_collection = AsyncMock()
    client.query_points = AsyncMock()
    return client


async def test_search_creates_collection_before_querying():
    with patch("cios.vector.tenant_store.AsyncQdrantClient") as mock_client_cls:
        client = _autospec_client()
        mock_client_cls.return_value = client

        collections_resp = MagicMock()
        collections_resp.collections = []  # tenant has never uploaded a document
        client.get_collections.return_value = collections_resp
        query_resp = MagicMock()
        query_resp.points = []
        client.query_points.return_value = query_resp

        store = TenantVectorStore("11111111-1111-1111-1111-111111111111")
        store._embed = AsyncMock(return_value=[0.0] * EMBEDDING_DIM)  # type: ignore[method-assign]

        results = await store.search(query="anything")

        assert results == []
        client.get_collections.assert_awaited_once()
        client.create_collection.assert_awaited_once()
        client.query_points.assert_awaited_once()


async def test_search_skips_create_when_collection_already_exists():
    with patch("cios.vector.tenant_store.AsyncQdrantClient") as mock_client_cls:
        client = _autospec_client()
        mock_client_cls.return_value = client

        existing = MagicMock()
        existing.name = "cios_tenant_11111111_1111_1111_1111_111111111111"
        collections_resp = MagicMock()
        collections_resp.collections = [existing]
        client.get_collections.return_value = collections_resp
        query_resp = MagicMock()
        query_resp.points = []
        client.query_points.return_value = query_resp

        store = TenantVectorStore("11111111-1111-1111-1111-111111111111")
        store._embed = AsyncMock(return_value=[0.0] * EMBEDDING_DIM)  # type: ignore[method-assign]

        await store.search(query="anything")

        client.get_collections.assert_awaited_once()
        client.create_collection.assert_not_awaited()
        client.query_points.assert_awaited_once()
