"""Knowledge Vault API — per-tenant private AI memory."""

import uuid
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select

from cios.core.dependencies import DB, Auth
from cios.models.knowledge_vault import KnowledgeDocument
from cios.models.tenant import AuditLog

router = APIRouter()
log = structlog.get_logger(__name__)

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
}

MAX_FILE_SIZE_MB = 50


class DocumentResponse(BaseModel):
    id: uuid.UUID
    title: str
    document_type: str
    description: str | None = None
    file_name: str | None = None
    file_size_bytes: int | None = None
    vectorization_status: str = "pending"
    is_vectorized: bool = False
    chunk_count: int = 0
    created_at: datetime
    tags: list[str] = []

    model_config = {"from_attributes": True}


class SearchRequest(BaseModel):
    query: str
    document_types: list[str] | None = None
    top_k: int = 10
    min_score: float = 0.6


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]


class UploadResponse(BaseModel):
    document_id: str
    task_id: str
    status: str
    message: str


class SearchResultItem(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    text: str
    score: float
    metadata: dict[str, Any]


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    query: str
    count: int


class DownloadUrlResponse(BaseModel):
    download_url: str
    expires_in: int


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    db: DB,
    user: Auth,
    document_type: str | None = Query(None),
    search: str | None = Query(None),
) -> dict[str, Any]:
    query = (
        select(KnowledgeDocument)
        .where(KnowledgeDocument.tenant_id == user.tenant_id)
        .order_by(KnowledgeDocument.created_at.desc())
    )

    if document_type:
        query = query.where(KnowledgeDocument.document_type == document_type)

    result = await db.execute(query)
    items = result.scalars().all()
    return {"items": [DocumentResponse.model_validate(i).model_dump() for i in items]}


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    db: DB,
    user: Auth,
    file: UploadFile = File(...),
    # These four were previously plain `str` params, which FastAPI reads as
    # unused Query parameters once an UploadFile/File sibling is present —
    # confirmed empirically against the pinned FastAPI version, not a style
    # nit. The multipart form fields the frontend actually sends were
    # silently discarded and every upload fell back to these defaults
    # (document_type always "general" regardless of the UI's dropdown,
    # tags/description always empty). Form(...) makes them real.
    document_type: str = Form("general"),
    title: str | None = Form(None),
    description: str | None = Form(None),
    tags: str = Form(""),
    # Required, no default: an explicit representation that this document
    # contains no CUI, classified, or export-controlled technical data (see
    # docs/legal/cui-restriction-draft.md). Paired with the automated
    # marking scan in tasks/ingestion.py — this is the attestation half,
    # that's the technical backstop.
    attestation: bool = Form(...),
) -> dict[str, Any]:
    """Upload a document to the Knowledge Vault. Ingestion and vectorization are async."""
    if not attestation:
        raise HTTPException(
            status_code=422,
            detail=(
                "You must confirm this document contains no CUI, classified, "
                "or export-controlled technical data before uploading."
            ),
        )

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.content_type}",
        )

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {size_mb:.1f}MB (max {MAX_FILE_SIZE_MB}MB)",
        )

    import json

    try:
        tag_list = (
            json.loads(tags)
            if tags.startswith("[")
            else [t.strip() for t in tags.split(",") if t.strip()]
        )
    except (json.JSONDecodeError, ValueError):
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    doc = KnowledgeDocument(
        tenant_id=user.tenant_id,
        title=title or file.filename or "Untitled",
        document_type=document_type,
        description=description,
        file_name=file.filename,
        file_size_bytes=len(content),
        mime_type=file.content_type,
        uploaded_by=user.user_id,
        vectorization_status="pending",
        tags=tag_list,
    )
    db.add(doc)
    await db.flush()

    from cios.core.storage import DocumentStorage, build_storage_key

    # Persist the original file before queueing ingestion — previously the
    # raw bytes only ever existed transiently inside the Celery task (see
    # tasks/ingestion.py), passed through Redis as a task argument and
    # discarded after text extraction. Nothing about the source document
    # survived, and there was no way for a tenant to ever retrieve what
    # they uploaded. Uploading here first, then queueing the task with the
    # storage key instead of the raw bytes, fixes both: the document is
    # actually kept, and the broker payload is a short string instead of
    # up to MAX_FILE_SIZE_MB of inline bytes.
    storage_key = build_storage_key(str(user.tenant_id), str(doc.id), file.filename)
    content_type = file.content_type or "application/octet-stream"
    await DocumentStorage().upload(storage_key, content, content_type)
    doc.s3_key = storage_key

    db.add(
        AuditLog(
            tenant_id=user.tenant_id,
            user_id=user.user_id,
            action="knowledge_vault_upload_attested",
            resource_type="knowledge_document",
            resource_id=str(doc.id),
            extra_metadata={"attestation_confirmed": True},
        )
    )
    await db.flush()

    from cios.tasks.ingestion import ingest_document

    task = ingest_document.delay(str(user.tenant_id), str(doc.id), storage_key, file.content_type)

    return {
        "document_id": str(doc.id),
        "task_id": task.id,
        "status": "queued",
        "message": "Document queued for ingestion and vectorization",
    }


@router.post("/search", response_model=SearchResponse)
async def search_knowledge_vault(body: SearchRequest, user: Auth) -> dict[str, Any]:
    """Semantic search across the tenant's Knowledge Vault using vector similarity."""
    from cios.vector.tenant_store import TenantVectorStore

    store = TenantVectorStore(str(user.tenant_id))
    raw = await store.search(
        query=body.query,
        top_k=body.top_k,
        min_score=body.min_score,
        filters={"document_type": body.document_types} if body.document_types else None,
    )
    results = [
        {
            "chunk_id": f"{r['doc_id']}:{r['chunk_index']}",
            "document_id": r["doc_id"],
            "document_title": (r.get("metadata") or {}).get("title", "Unknown Document"),
            "text": r["text"],
            "score": r["score"],
            "metadata": r.get("metadata") or {},
        }
        for r in raw
    ]
    return {"results": results, "query": body.query, "count": len(results)}


@router.get("/{document_id}/download", response_model=DownloadUrlResponse)
async def get_document_download_url(document_id: uuid.UUID, db: DB, user: Auth) -> dict[str, Any]:
    """Presigned URL to fetch the original uploaded file. Short-lived and
    tenant-scoped like every other document lookup here — the tenant_id
    filter below is what stops a document_id guess from leaking another
    tenant's file, since the presigned URL itself carries no tenant check
    once issued."""
    result = await db.execute(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.tenant_id == user.tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc.s3_key:
        raise HTTPException(
            status_code=404,
            detail="No stored file for this document (uploaded before object storage was wired up)",
        )

    from cios.core.storage import DocumentStorage

    expires_in = 300
    url = await DocumentStorage().presigned_download_url(doc.s3_key, expires_in=expires_in)
    return {"download_url": url, "expires_in": expires_in}


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: uuid.UUID, db: DB, user: Auth) -> None:
    result = await db.execute(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.tenant_id == user.tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.qdrant_collection:
        from cios.vector.tenant_store import TenantVectorStore

        store = TenantVectorStore(str(user.tenant_id))
        try:
            await store.delete_document(str(document_id))
        except Exception:
            # A Qdrant hiccup (unreachable, timeout, misconfigured client)
            # must not block the user from deleting their own row — this is
            # vector cleanup, not the primary action, same reasoning as
            # search's "except Exception: knowledge_context = []" elsewhere
            # in this codebase. Previously this raised straight out of the
            # endpoint, so the Postgres delete below never ran and every
            # delete failed outright ("Delete failed") whenever Qdrant had
            # any issue, even though nothing about the user's own document
            # row was actually broken. Trade-off: search's results come
            # straight from each chunk's Qdrant payload, not a join back to
            # this table, so an orphaned chunk can still surface in semantic
            # search for a document that no longer exists here — logged as a
            # warning so that's visible, but still better than refusing to
            # delete the user's own document at all.
            log.warning(
                "knowledge_vault_qdrant_delete_failed",
                document_id=str(document_id),
                tenant_id=str(user.tenant_id),
                exc_info=True,
            )

    if doc.s3_key:
        from cios.core.storage import DocumentStorage

        try:
            await DocumentStorage().delete(doc.s3_key)
        except Exception:
            # Same reasoning as the Qdrant cleanup above: an object-storage
            # hiccup must not block deleting the user's own row.
            log.warning(
                "knowledge_vault_s3_delete_failed",
                document_id=str(document_id),
                tenant_id=str(user.tenant_id),
                exc_info=True,
            )

    await db.delete(doc)
