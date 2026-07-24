"""Agent execution audit trail — every AI run is logged and traceable."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cios.core.database import Base

from .base import TenantMixin, TimestampMixin, UUIDMixin


class AgentRun(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """
    Immutable record of every agent invocation.
    Every recommendation surfaced to a user traces to an AgentRun.
    """

    __tablename__ = "agent_runs"
    __table_args__ = (
        Index("idx_ar_tenant_type", "tenant_id", "agent_type"),
        Index("idx_ar_resource", "resource_type", "resource_id"),
    )

    agent_type: Mapped[str] = mapped_column(String(64), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))

    status: Mapped[str] = mapped_column(String(32), default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)

    # AI metadata
    model_used: Mapped[str | None] = mapped_column(String(64))
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    total_cost_usd: Mapped[float | None] = mapped_column(Float)

    # Result
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)

    # Procurement rule reference
    rule_pack: Mapped[str | None] = mapped_column(String(64))
    rule_citations: Mapped[list] = mapped_column(JSONB, default=list)

    # Input snapshot (for auditability and reproducibility)
    input_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    steps: Mapped[list["AgentRunStep"]] = relationship(
        back_populates="agent_run", cascade="all, delete-orphan"
    )


class AgentRunStep(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "agent_run_steps"

    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
    )
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    step_name: Mapped[str] = mapped_column(String(128), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    input_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    output_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    reasoning: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)

    agent_run: Mapped["AgentRun"] = relationship(back_populates="steps")
