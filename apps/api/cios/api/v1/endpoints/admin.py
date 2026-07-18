"""Internal admin API — requires admin API key, not tenant auth."""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select, func

from cios.config import settings
from cios.core.database import get_db
from cios.models.tenant import Tenant
from cios.models.subscription import Subscription

router = APIRouter()


async def require_admin_key(x_admin_key: str = Header(...)) -> None:
    import hmac
    import hashlib
    expected = hashlib.sha256(settings.jwt_secret.encode()).hexdigest()
    if not hmac.compare_digest(x_admin_key, expected):
        raise HTTPException(status_code=403, detail="Invalid admin key")


@router.get("/stats", dependencies=[Depends(require_admin_key)])
async def platform_stats(db=Depends(get_db)) -> dict:
    tenant_count = (await db.execute(select(func.count(Tenant.id)))).scalar_one()
    active_subs = (
        await db.execute(
            select(func.count(Subscription.id)).where(Subscription.status == "active")
        )
    ).scalar_one()

    return {
        "tenants": tenant_count,
        "active_subscriptions": active_subs,
        "platform_version": "1.0.0",
    }


@router.get("/tenants", dependencies=[Depends(require_admin_key)])
async def list_all_tenants(db=Depends(get_db)) -> dict:
    result = await db.execute(
        select(Tenant).order_by(Tenant.created_at.desc()).limit(100)
    )
    tenants = result.scalars().all()
    return {
        "tenants": [
            {"id": str(t.id), "name": t.name, "slug": t.slug, "plan": t.plan, "is_active": t.is_active}
            for t in tenants
        ]
    }
