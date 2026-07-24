"""Subscription and billing models."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from cios.core.database import Base

from .base import TimestampMixin, UUIDMixin


class Subscription(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("idx_sub_tenant", "tenant_id"),
        Index("idx_sub_stripe_id", "stripe_subscription_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    plan: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active")
    stripe_customer_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    stripe_price_id: Mapped[str | None] = mapped_column(String(128))
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trial_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool | None] = mapped_column()
    seats: Mapped[int] = mapped_column(Integer, default=1)
    features: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class Invoice(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "invoices"

    tenant_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    stripe_invoice_id: Mapped[str] = mapped_column(String(128), unique=True)
    amount_due: Mapped[float] = mapped_column(Float, nullable=False)
    amount_paid: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    invoice_pdf_url: Mapped[str | None] = mapped_column(String(512))
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
