"""Knowledge Vault models — per-tenant private AI memory."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cios.core.database import Base

from .base import TenantMixin, TimestampMixin, UUIDMixin


class KnowledgeDocument(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """A document ingested into the tenant's Knowledge Vault."""

    __tablename__ = "knowledge_documents"
    __table_args__ = (Index("idx_kd_tenant_type", "tenant_id", "document_type"),)

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    s3_key: Mapped[str | None] = mapped_column(String(512))
    file_name: Mapped[str | None] = mapped_column(String(256))
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    mime_type: Mapped[str | None] = mapped_column(String(128))
    page_count: Mapped[int | None] = mapped_column(Integer)

    # Parsed content
    extracted_text: Mapped[str | None] = mapped_column(Text)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    description: Mapped[str | None] = mapped_column(Text)

    # Vector status
    vectorization_status: Mapped[str] = mapped_column(String(32), default="pending")
    is_vectorized: Mapped[bool] = mapped_column(Boolean, default=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    vectorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    qdrant_collection: Mapped[str | None] = mapped_column(String(128))

    # Associations
    related_opportunity_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    is_confidential: Mapped[bool] = mapped_column(Boolean, default=True)

    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class KnowledgeChunk(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """A vectorized chunk of a Knowledge Vault document."""

    __tablename__ = "knowledge_chunks"
    __table_args__ = (Index("idx_kc_document", "document_id"),)

    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer)
    qdrant_point_id: Mapped[str | None] = mapped_column(String(64), index=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    document: Mapped["KnowledgeDocument"] = relationship(back_populates="chunks")
