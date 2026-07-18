"""
Per-tenant vector store — isolated Qdrant collections per tenant.

Design: each tenant gets their own Qdrant collection prefixed with
their tenant_id. Documents are NEVER cross-contaminated between tenants.
Embeddings are generated using Anthropic or OpenAI compatible models.
"""
import hashlib
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PointStruct,
    VectorParams,
)

from cios.config import settings

EMBEDDING_DIM = 1024  # voyage-3 native dimension
COLLECTION_PREFIX = "cios_tenant"


class TenantVectorStore:
    """Isolated vector store for a single tenant."""

    def __init__(self, tenant_id: str) -> None:
        self.tenant_id = tenant_id
        self.collection_name = f"{COLLECTION_PREFIX}_{tenant_id.replace('-', '_')}"
        self._client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )

    async def ensure_collection(self) -> None:
        """Create collection if it doesn't exist."""
        collections = await self._client.get_collections()
        names = [c.name for c in collections.collections]
        if self.collection_name not in names:
            await self._client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
            )

    async def upsert(
        self,
        doc_id: str,
        chunk_index: int,
        text: str,
        embedding: list[float],
        metadata: dict[str, Any],
    ) -> str:
        """Insert or update a document chunk."""
        await self.ensure_collection()
        point_id = _deterministic_uuid(f"{doc_id}:{chunk_index}")

        await self._client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "doc_id": doc_id,
                        "chunk_index": chunk_index,
                        "text": text[:2000],
                        "tenant_id": self.tenant_id,
                        **metadata,
                    },
                )
            ],
        )
        return point_id

    async def search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search with optional metadata filters."""
        embedding = await self._embed(query)
        qdrant_filter = self._build_filter(filters) if filters else None

        results = await self._client.search(
            collection_name=self.collection_name,
            query_vector=embedding,
            limit=top_k,
            score_threshold=min_score,
            query_filter=qdrant_filter,
            with_payload=True,
        )

        return [
            {
                "doc_id": r.payload.get("doc_id"),
                "chunk_index": r.payload.get("chunk_index"),
                "text": r.payload.get("text"),
                "score": r.score,
                "metadata": {k: v for k, v in r.payload.items() if k not in ("text", "doc_id", "chunk_index", "tenant_id")},
            }
            for r in results
        ]

    async def delete_document(self, doc_id: str) -> None:
        """Delete all chunks for a document."""
        await self._client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            ),
        )

    async def delete_collection(self) -> None:
        """Delete entire tenant collection — used when tenant is deleted."""
        await self._client.delete_collection(self.collection_name)

    async def _embed(self, text: str) -> list[float]:
        """Generate embedding via Voyage AI (voyage-3, 1024-dim → padded to EMBEDDING_DIM)."""
        import voyageai
        client = voyageai.AsyncClient(api_key=settings.voyage_api_key)
        result = await client.embed([text[:8000]], model=settings.embedding_model, input_type="document")
        return result.embeddings[0]

    def _build_filter(self, filters: dict[str, Any]) -> Filter:
        conditions = []
        for key, value in filters.items():
            if isinstance(value, list):
                conditions.append(FieldCondition(key=key, match=MatchAny(any=value)))
            else:
                conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
        return Filter(must=conditions)


def _deterministic_uuid(seed: str) -> str:
    """Deterministic UUID from a string seed (for idempotent upserts)."""
    h = hashlib.md5(seed.encode(), usedforsecurity=False).hexdigest()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"
