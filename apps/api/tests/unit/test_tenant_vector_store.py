"""TenantVectorStore.search() must create the tenant's Qdrant collection
before querying it.

Regression test for a bug where search() (unlike upsert()) never called
ensure_collection(). A tenant who had never uploaded a document — so their
collection was never created — got an unhandled 404 from Qdrant on their
first Knowledge Vault search. That exception wasn't an HTTPException, so it
escaped FastAPI's ExceptionMiddleware (which sits inside CORSMiddleware) and
was caught instead by the outer ServerErrorMiddleware, whose 500 response
never passes back through CORSMiddleware's header-adding logic — so the
browser reported it as a CORS failure rather than the real 500.
"""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://cios_user:cios_pass@localhost/x")
os.environ.setdefault("JWT_SECRET", "test_secret_minimum_32_characters_long")
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)
os.environ.setdefault("ANTHROPIC_API_KEY", "test_key")

from unittest.mock import AsyncMock, MagicMock, patch

from cios.vector.tenant_store import EMBEDDING_DIM, TenantVectorStore


async def test_search_creates_collection_before_querying():
    with patch("cios.vector.tenant_store.AsyncQdrantClient") as MockClient:
        client = MockClient.return_value
        collections_resp = MagicMock()
        collections_resp.collections = []  # tenant has never uploaded a document
        client.get_collections = AsyncMock(return_value=collections_resp)
        client.create_collection = AsyncMock()
        client.search = AsyncMock(return_value=[])

        store = TenantVectorStore("11111111-1111-1111-1111-111111111111")
        store._embed = AsyncMock(return_value=[0.0] * EMBEDDING_DIM)  # type: ignore[method-assign]

        results = await store.search(query="anything")

        assert results == []
        client.get_collections.assert_awaited_once()
        client.create_collection.assert_awaited_once()
        client.search.assert_awaited_once()


async def test_search_skips_create_when_collection_already_exists():
    with patch("cios.vector.tenant_store.AsyncQdrantClient") as MockClient:
        client = MockClient.return_value
        existing = MagicMock()
        existing.name = "cios_tenant_11111111_1111_1111_1111_111111111111"
        collections_resp = MagicMock()
        collections_resp.collections = [existing]
        client.get_collections = AsyncMock(return_value=collections_resp)
        client.create_collection = AsyncMock()
        client.search = AsyncMock(return_value=[])

        store = TenantVectorStore("11111111-1111-1111-1111-111111111111")
        store._embed = AsyncMock(return_value=[0.0] * EMBEDDING_DIM)  # type: ignore[method-assign]

        await store.search(query="anything")

        client.get_collections.assert_awaited_once()
        client.create_collection.assert_not_awaited()
        client.search.assert_awaited_once()
