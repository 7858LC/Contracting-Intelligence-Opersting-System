"""Document ingestion and vectorization tasks."""

import asyncio
import hashlib
import uuid

from cios.tasks import celery_app


@celery_app.task(bind=True, max_retries=3, soft_time_limit=300)
def ingest_document(
    self, tenant_id: str, document_id: str, storage_key: str, mime_type: str
) -> dict:
    return asyncio.run(_ingest_async(tenant_id, document_id, storage_key, mime_type))


async def _ingest_async(tenant_id: str, document_id: str, storage_key: str, mime_type: str) -> dict:
    from datetime import UTC, datetime

    from sqlalchemy import select
    from sqlalchemy import text as sql_text

    from cios.core.database import async_session_factory
    from cios.models.knowledge_vault import KnowledgeChunk, KnowledgeDocument
    from cios.models.tenant import AuditLog

    async with async_session_factory() as db:
        # knowledge_documents/knowledge_chunks are FORCE ROW LEVEL SECURITY
        # (alembic/versions/007_force_rls.py) — this task runs outside the
        # request lifecycle on its own session, so nothing sets
        # app.current_tenant unless this does. Without it, the query below
        # sees zero rows under RLS and every ingestion silently no-ops.
        await db.execute(
            sql_text("SELECT set_config('app.current_tenant', :tenant_id, false)"),
            {"tenant_id": tenant_id},
        )

        result = await db.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.id == uuid.UUID(document_id))
        )
        doc = result.scalar_one_or_none()
        if not doc:
            return {"error": "document not found"}

        doc.vectorization_status = "processing"
        await db.commit()

        try:
            from cios.core.cui_screening import scan_for_restricted_markings
            from cios.core.storage import DocumentStorage
            from cios.vector.tenant_store import TenantVectorStore

            # Previously the caller (knowledge_vault.py's upload endpoint)
            # passed the raw file bytes straight through as a task argument
            # — up to MAX_FILE_SIZE_MB inline in the Celery/Redis broker,
            # and never persisted anywhere, so the original document was
            # unrecoverable the moment this task finished. The endpoint now
            # uploads to object storage first and hands this task a short
            # key instead.
            content = await DocumentStorage().download(storage_key)
            text = _extract_text(content, mime_type)

            # Screen for CUI/classification/export-control banner markings
            # before anything derived from the content is stored or sent to
            # a Claude call for vectorization/search. See
            # cios/core/cui_screening.py and docs/legal/cui-restriction-draft.md.
            # This runs here (not in the upload endpoint) because text
            # extraction from PDF/DOCX is real CPU work that shouldn't block
            # the API's event loop — this task already pays that cost.
            marking_matches = scan_for_restricted_markings(text)
            if marking_matches:
                doc.vectorization_status = "blocked_cui"
                doc.extra_metadata = {
                    **(doc.extra_metadata or {}),
                    "cui_screen_matches": marking_matches,
                }
                db.add(
                    AuditLog(
                        tenant_id=uuid.UUID(tenant_id),
                        user_id=doc.uploaded_by,
                        action="knowledge_vault_upload_blocked_cui_marking",
                        resource_type="knowledge_document",
                        resource_id=document_id,
                        extra_metadata={"matches": marking_matches},
                    )
                )
                try:
                    await DocumentStorage().delete(storage_key)
                except Exception:
                    # Best-effort — same reasoning as the S3/Qdrant cleanup
                    # in knowledge_vault.py's delete_document: a storage
                    # hiccup here must not stop the document being marked
                    # blocked, which is the safety-relevant part.
                    pass
                await db.commit()
                return {
                    "document_id": document_id,
                    "status": "blocked_cui",
                    "matches": marking_matches,
                }

            chunks = _chunk_text(text)
            content_hash = hashlib.sha256(content).hexdigest()

            doc.extracted_text = text[:50000]
            doc.content_hash = content_hash
            doc.chunk_count = len(chunks)

            store = TenantVectorStore(tenant_id)
            await store.ensure_collection()

            for i, chunk_text in enumerate(chunks):
                embedding = await store._embed(chunk_text)
                point_id = await store.upsert(
                    doc_id=document_id,
                    chunk_index=i,
                    text=chunk_text,
                    embedding=embedding,
                    metadata={"document_type": doc.document_type, "title": doc.title},
                )
                chunk = KnowledgeChunk(
                    tenant_id=uuid.UUID(tenant_id),
                    document_id=uuid.UUID(document_id),
                    chunk_index=i,
                    content=chunk_text,
                    token_count=len(chunk_text.split()) * 4 // 3,
                    qdrant_point_id=point_id,
                )
                db.add(chunk)

            doc.is_vectorized = True
            doc.vectorization_status = "completed"
            doc.vectorized_at = datetime.now(UTC)
            doc.qdrant_collection = store.collection_name
        except Exception:
            doc.vectorization_status = "failed"
            await db.commit()
            raise

        await db.commit()

    return {"document_id": document_id, "chunks": len(chunks)}


def _extract_text(content: bytes, mime_type: str) -> str:
    if mime_type == "application/pdf":
        try:
            import io

            import pypdf

            reader = pypdf.PdfReader(io.BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            return content.decode("utf-8", errors="ignore")
    elif "wordprocessingml" in mime_type:
        try:
            import io

            import docx

            doc = docx.Document(io.BytesIO(content))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            return content.decode("utf-8", errors="ignore")
    else:
        return content.decode("utf-8", errors="ignore")


def _chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


@celery_app.task(bind=True, max_retries=3)
def vectorize_past_performance(self, tenant_id: str, pp_id: str) -> dict:
    return asyncio.run(_vectorize_pp_async(tenant_id, pp_id))


async def _vectorize_pp_async(tenant_id: str, pp_id: str) -> dict:
    from sqlalchemy import select

    from cios.core.database import async_session_factory
    from cios.models.past_performance import PastPerformance

    async with async_session_factory() as db:
        result = await db.execute(
            select(PastPerformance).where(PastPerformance.id == uuid.UUID(pp_id))
        )
        pp = result.scalar_one_or_none()
        if not pp:
            return {"error": "past performance not found"}

    return {"pp_id": pp_id, "status": "vectorized"}
