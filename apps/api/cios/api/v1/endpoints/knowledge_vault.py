"""Knowledge Vault API — per-tenant private AI memory."""

import uuid
from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select

from cios.core.dependencies import DB, Auth
from cios.models.knowledge_vault import KnowledgeDocument

router = APIRouter()

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
    created_at: Any = None
    tags: list = []

    model_config = {"from_attributes": True}


class SearchRequest(BaseModel):
    query: str
    document_types: list[str] | None = None
    top_k: int = 10
    min_score: float = 0.6


@router.get("", response_model=dict[str, Any])
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


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    db: DB,
    user: Auth,
    file: UploadFile = File(...),
    document_type: str = "general",
    title: str | None = None,
    description: str | None = None,
    tags: str = "",
) -> dict[str, Any]:
    """Upload a document to the Knowledge Vault. Ingestion and vectorization are async."""
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

    from cios.tasks.ingestion import ingest_document

    task = ingest_document.delay(str(user.tenant_id), str(doc.id), content, file.content_type)

    return {
        "document_id": str(doc.id),
        "task_id": task.id,
        "status": "queued",
        "message": "Document queued for ingestion and vectorization",
    }


@router.post("/search")
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
        await store.delete_document(str(document_id))

    await db.delete(doc)
