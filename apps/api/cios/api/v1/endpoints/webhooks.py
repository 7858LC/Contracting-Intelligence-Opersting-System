"""Stripe webhook handler."""

import structlog
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from cios.config import settings

log = structlog.get_logger(__name__)
router = APIRouter()


class WebhookReceivedResponse(BaseModel):
    status: str


@router.post("/stripe", response_model=WebhookReceivedResponse)
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)) -> dict:
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook not configured")

    payload = await request.body()

    import stripe

    stripe.api_key = settings.stripe_secret_key

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    log.info("stripe_webhook", event_type=event["type"])

    from cios.tasks.billing import handle_stripe_event

    handle_stripe_event.delay(event["type"], event["data"]["object"])

    return {"status": "received"}
