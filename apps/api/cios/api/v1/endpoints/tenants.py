"""Tenant management API."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from cios.core.dependencies import Auth, AdminAuth, DB
from cios.models.tenant import Tenant, TenantMember

router = APIRouter()


class TenantProfileUpdate(BaseModel):
    name: str | None = None
    naics_codes: list[str] | None = None
    cage_code: str | None = None
    duns_number: str | None = None
    sam_unique_id: str | None = None
    small_business_designations: list[str] | None = None
    annual_revenue_band: str | None = None
    employee_count_band: str | None = None
    primary_jurisdictions: list[str] | None = None


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: str = "member"


@router.get("/profile")
async def get_tenant_profile(db: DB, user: Auth) -> dict:
    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant.to_dict()


@router.patch("/profile")
async def update_tenant_profile(body: TenantProfileUpdate, db: DB, user: AdminAuth) -> dict:
    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(tenant, k, v)
    return tenant.to_dict()


@router.get("/members")
async def list_members(db: DB, user: Auth) -> dict:
    result = await db.execute(
        select(TenantMember)
        .where(TenantMember.tenant_id == user.tenant_id, TenantMember.is_active == True)  # noqa: E712
        .order_by(TenantMember.created_at)
    )
    members = result.scalars().all()
    return {
        "members": [
            {"id": str(m.id), "email": m.email, "full_name": m.full_name, "role": m.role}
            for m in members
        ]
    }


@router.post("/members/invite")
async def invite_member(body: InviteMemberRequest, db: DB, user: AdminAuth) -> dict:
    from cios.tasks.email import send_invite_email
    import secrets
    from datetime import UTC, datetime, timedelta
    from cios.models.tenant import TenantInvite

    token = secrets.token_urlsafe(32)
    invite = TenantInvite(
        tenant_id=user.tenant_id,
        email=body.email,
        role=body.role,
        token=token,
        expires_at=datetime.now(UTC) + timedelta(days=7),
        invited_by=user.user_id,
    )
    db.add(invite)
    await db.flush()
    send_invite_email.delay(str(user.tenant_id), body.email, token)
    return {"status": "invited", "email": body.email}
