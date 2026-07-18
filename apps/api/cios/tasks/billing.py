"""Stripe billing event handler."""
import asyncio
import structlog
from cios.tasks import celery_app

log = structlog.get_logger(__name__)


@celery_app.task(bind=True, max_retries=3)
def handle_stripe_event(self, event_type: str, event_data: dict) -> dict:
    return asyncio.get_event_loop().run_until_complete(
        _handle_async(event_type, event_data)
    )


async def _handle_async(event_type: str, event_data: dict) -> dict:
    from cios.core.database import async_session_factory
    from cios.models.subscription import Subscription
    from sqlalchemy import select

    log.info("stripe_event", type=event_type)

    if event_type == "customer.subscription.updated":
        async with async_session_factory() as db:
            stripe_sub_id = event_data.get("id")
            result = await db.execute(
                select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
            )
            sub = result.scalar_one_or_none()
            if sub:
                sub.status = event_data.get("status", sub.status)
                sub.plan = event_data.get("metadata", {}).get("plan", sub.plan)
                await db.commit()

    elif event_type == "invoice.payment_succeeded":
        from cios.models.subscription import Invoice
        import uuid
        from datetime import datetime, UTC
        async with async_session_factory() as db:
            tenant_id = event_data.get("metadata", {}).get("tenant_id")
            if tenant_id:
                inv = Invoice(
                    tenant_id=uuid.UUID(tenant_id),
                    stripe_invoice_id=event_data.get("id", ""),
                    amount_due=event_data.get("amount_due", 0) / 100,
                    amount_paid=event_data.get("amount_paid", 0) / 100,
                    currency=event_data.get("currency", "usd").upper(),
                    status="paid",
                    paid_at=datetime.now(UTC),
                )
                db.add(inv)
                await db.commit()

    return {"event_type": event_type, "processed": True}
