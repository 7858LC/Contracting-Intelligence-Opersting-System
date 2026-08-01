"""Subscription & Billing API — Stripe integration."""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from cios.config import settings
from cios.core.dependencies import DB, AdminAuth, Auth
from cios.core.features import features_for_plan
from cios.models.subscription import Invoice, Subscription

router = APIRouter()


class CreateCheckoutRequest(BaseModel):
    plan: str
    seats: int = 1
    success_url: str = "/dashboard/settings?checkout=success"
    cancel_url: str = "/dashboard/settings"


class PortalRequest(BaseModel):
    return_url: str = "/dashboard/settings"


class SubscriptionResponse(BaseModel):
    # Only plan/status/features are guaranteed — a trial tenant with no
    # Subscription row yet gets a sparse fallback (see get_subscription
    # below), so everything else must be optional to cover both shapes.
    id: uuid.UUID | None = None
    tenant_id: uuid.UUID | None = None
    plan: str
    status: str
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    stripe_price_id: str | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    trial_end: datetime | None = None
    cancel_at_period_end: bool | None = None
    seats: int | None = None
    features: dict[str, Any]
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class CheckoutSessionResponse(BaseModel):
    url: str
    checkout_url: str
    session_id: str


class PortalSessionResponse(BaseModel):
    url: str
    portal_url: str


class InvoiceResponse(BaseModel):
    id: uuid.UUID
    stripe_invoice_id: str
    amount_due: float
    amount_paid: float | None
    currency: str
    status: str
    invoice_pdf_url: str | None
    period_start: datetime | None
    period_end: datetime | None
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InvoiceListResponse(BaseModel):
    invoices: list[InvoiceResponse]


@router.get("/current", response_model=SubscriptionResponse)
async def get_subscription(db: DB, user: Auth) -> dict:
    result = await db.execute(
        select(Subscription)
        .where(Subscription.tenant_id == user.tenant_id)
        .order_by(Subscription.created_at.desc())
    )
    sub = result.scalars().first()
    if not sub:
        return {"plan": "trial", "status": "active", "features": features_for_plan("trial")}
    return {**sub.to_dict(), "features": features_for_plan(sub.plan)}


@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(body: CreateCheckoutRequest, user: AdminAuth) -> dict:
    """Create a Stripe Checkout session."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing not configured")

    price_map = {
        "starter": settings.stripe_price_starter,
        "professional": settings.stripe_price_professional,
        "growth": settings.stripe_price_growth,
        "enterprise": settings.stripe_price_enterprise,
    }
    price_id = price_map.get(body.plan)
    if not price_id:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {body.plan}")

    import stripe

    stripe.api_key = settings.stripe_secret_key

    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": body.seats}],
        success_url=body.success_url,
        cancel_url=body.cancel_url,
        metadata={"tenant_id": str(user.tenant_id), "plan": body.plan},
    )
    return {"url": session.url, "checkout_url": session.url, "session_id": session.id}


@router.post("/portal", response_model=PortalSessionResponse)
async def customer_portal(db: DB, user: Auth, body: PortalRequest = None) -> dict:
    """Stripe customer portal for billing management."""
    return_url = body.return_url if body else "/dashboard/settings"
    result = await db.execute(select(Subscription).where(Subscription.tenant_id == user.tenant_id))
    sub = result.scalars().first()
    if not sub or not sub.stripe_customer_id:
        raise HTTPException(status_code=404, detail="No active subscription")

    import stripe

    stripe.api_key = settings.stripe_secret_key
    session = stripe.billing_portal.Session.create(
        customer=sub.stripe_customer_id,
        return_url=return_url,
    )
    return {"url": session.url, "portal_url": session.url}


@router.get("/invoices", response_model=InvoiceListResponse)
async def list_invoices(db: DB, user: Auth) -> dict:
    result = await db.execute(
        select(Invoice)
        .where(Invoice.tenant_id == user.tenant_id)
        .order_by(Invoice.created_at.desc())
        .limit(24)
    )
    return {"invoices": result.scalars().all()}
