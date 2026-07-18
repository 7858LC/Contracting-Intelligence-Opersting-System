"""Subscription & Billing API — Stripe integration."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from cios.config import settings
from cios.core.dependencies import Auth, DB, AdminAuth
from cios.models.subscription import Subscription, Invoice

router = APIRouter()


class CreateCheckoutRequest(BaseModel):
    plan: str
    seats: int = 1
    success_url: str = "/dashboard/settings?checkout=success"
    cancel_url: str = "/dashboard/settings"


class PortalRequest(BaseModel):
    return_url: str = "/dashboard/settings"


PLAN_FEATURES = {
    "starter": {
        "opportunities": 50,
        "simulations": 5,
        "knowledge_vault_mb": 500,
        "seats": 3,
        "api_access": False,
        "award_simulator": True,
        "competitive_intel": False,
    },
    "professional": {
        "opportunities": 500,
        "simulations": 50,
        "knowledge_vault_mb": 5000,
        "seats": 10,
        "api_access": True,
        "award_simulator": True,
        "competitive_intel": True,
    },
    "enterprise": {
        "opportunities": -1,
        "simulations": -1,
        "knowledge_vault_mb": -1,
        "seats": -1,
        "api_access": True,
        "award_simulator": True,
        "competitive_intel": True,
        "customer_owned_keys": True,
        "sso": True,
        "dedicated_support": True,
    },
}


@router.get("/current")
async def get_subscription(db: DB, user: Auth) -> dict:
    result = await db.execute(
        select(Subscription).where(Subscription.tenant_id == user.tenant_id)
        .order_by(Subscription.created_at.desc())
    )
    sub = result.scalars().first()
    if not sub:
        return {"plan": "trial", "status": "active", "features": PLAN_FEATURES.get("starter", {})}
    return {**sub.to_dict(), "features": PLAN_FEATURES.get(sub.plan, {})}


@router.post("/checkout")
async def create_checkout_session(body: CreateCheckoutRequest, user: AdminAuth) -> dict:
    """Create a Stripe Checkout session."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing not configured")

    price_map = {
        "starter": settings.stripe_price_starter,
        "professional": settings.stripe_price_professional,
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


@router.post("/portal")
async def customer_portal(db: DB, user: Auth, body: PortalRequest = None) -> dict:
    """Stripe customer portal for billing management."""
    return_url = body.return_url if body else "/dashboard/settings"
    result = await db.execute(
        select(Subscription).where(Subscription.tenant_id == user.tenant_id)
    )
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


@router.get("/invoices")
async def list_invoices(db: DB, user: Auth) -> dict:
    result = await db.execute(
        select(Invoice)
        .where(Invoice.tenant_id == user.tenant_id)
        .order_by(Invoice.created_at.desc())
        .limit(24)
    )
    return {"invoices": [i.to_dict() for i in result.scalars().all()]}
