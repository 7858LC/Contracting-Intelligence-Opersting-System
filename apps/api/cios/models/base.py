"""Shared model mixins and base classes."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, String, inspect, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize model columns to a JSON-safe dict."""
        result = {}
        for col in inspect(self.__class__).columns:
            val = getattr(self, col.name, None)
            if isinstance(val, uuid.UUID):
                result[col.name] = str(val)
            elif isinstance(val, datetime):
                result[col.name] = val.isoformat()
            else:
                result[col.name] = val
        return result


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
    )


class TenantMixin:
    """Row-level security anchor — every tenant-scoped model must include this."""

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )


class EvidenceMixin:
    """Stores AI recommendation evidence for auditability."""

    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(nullable=True)
    ai_model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
