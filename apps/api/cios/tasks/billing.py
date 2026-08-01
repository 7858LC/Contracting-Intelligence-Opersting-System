"""Stripe billing event handler."""

import asyncio

import structlog

from cios.tasks import celery_app

log = structlog.get_logger(__name__)


@celery_app.task(bind=True, max_retries=3)
def handle_stripe_event(self, event_type: str, event_data: dict) -> dict:
    return asyncio.run(_handle_async(event_type, event_data))


async def _handle_async(event_type: str, event_data: dict) -> dict:
    from sqlalchemy import select

    from cios.core.database import async_session_factory
    from cios.models.subscription import Subscription
    from cios.models.tenant import Tenant

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
                new_plan = event_data.get("metadata", {}).get("plan", sub.plan)
                sub.plan = new_plan
                # Subscription.plan alone gates nothing — every feature check
                # (hasFeature(), require_feature(), the JWT "plan" claim) reads
                # Tenant.plan, so a completed upgrade has to land here too or
                # the tenant keeps their old plan's access forever.
                tenant = await db.get(Tenant, sub.tenant_id)
                if tenant and new_plan:
                    tenant.plan = new_plan
                await db.commit()

    elif event_type == "invoice.payment_succeeded":
        import uuid
        from datetime import UTC, datetime

        from cios.models.subscription import Invoice

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
