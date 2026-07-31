"""Tenant management API."""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from cios.core.dependencies import DB, AdminAuth, Auth
from cios.core.security import generate_api_key
from cios.models.tenant import ApiKey, Tenant, TenantMember

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


class TenantProfileResponse(BaseModel):
    # encryption_key_reference deliberately excluded — a KMS key reference
    # has no reason to ever leave the backend, and to_dict()'s generic
    # column dump was sending it to every authenticated tenant user before
    # this response_model existed to filter it out.
    id: uuid.UUID
    name: str
    slug: str
    plan: str
    is_active: bool
    settings: dict
    naics_codes: list
    cage_code: str | None
    duns_number: str | None
    sam_unique_id: str | None
    small_business_designations: list
    annual_revenue_band: str | None
    employee_count_band: str | None
    primary_jurisdictions: list
    is_council_member: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: str = "member"


class InviteMemberResponse(BaseModel):
    status: str
    email: str
    invite_url: str


class MemberResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    role: str


class MemberListResponse(BaseModel):
    members: list[MemberResponse]


class ApiKeyCreate(BaseModel):
    name: str


class ApiKeyCreatedResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    plaintext_key: str
    created_at: str


class ApiKeySummaryResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    created_at: str


class ApiKeyListResponse(BaseModel):
    api_keys: list[ApiKeySummaryResponse]


class RevokedResponse(BaseModel):
    revoked: bool


@router.get("/profile", response_model=TenantProfileResponse)
async def get_tenant_profile(db: DB, user: Auth) -> Tenant:
    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.patch("/profile", response_model=TenantProfileResponse)
async def update_tenant_profile(body: TenantProfileUpdate, db: DB, user: AdminAuth) -> Tenant:
    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(tenant, k, v)
    return tenant


@router.get("/members", response_model=MemberListResponse)
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


@router.post("/members/invite", response_model=InviteMemberResponse)
async def invite_member(body: InviteMemberRequest, db: DB, user: AdminAuth) -> InviteMemberResponse:
    import secrets
    from datetime import UTC, timedelta

    from cios.config import settings
    from cios.models.tenant import TenantInvite
    from cios.tasks.email import send_invite_email

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

    # Returned regardless of whether the email actually sends (SendGrid may
    # not be configured, or may fail) — this is the reliable path to get an
    # invited teammate in: copy/paste the link rather than depend on email
    # delivery succeeding.
    invite_url = f"{settings.app_url}/auth/accept-invite?token={token}"
    return InviteMemberResponse(status="invited", email=body.email, invite_url=invite_url)


@router.post("/api-keys", response_model=ApiKeyCreatedResponse)
async def create_api_key(body: ApiKeyCreate, db: DB, user: AdminAuth) -> dict:
    plaintext, key_hash = generate_api_key("cios")
    api_key = ApiKey(
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        name=body.name,
        key_hash=key_hash,
        key_prefix=plaintext[:12],
    )
    db.add(api_key)
    await db.flush()
    return {
        "id": str(api_key.id),
        "name": api_key.name,
        "key_prefix": api_key.key_prefix,
        "plaintext_key": plaintext,
        "created_at": api_key.created_at.isoformat(),
    }


@router.get("/api-keys", response_model=ApiKeyListResponse)
async def list_api_keys(db: DB, user: Auth) -> dict:
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.tenant_id == user.tenant_id, ApiKey.is_active == True)  # noqa: E712
        .order_by(ApiKey.created_at.desc())
    )
    return {
        "api_keys": [
            {
                "id": str(k.id),
                "name": k.name,
                "key_prefix": k.key_prefix,
                "created_at": k.created_at.isoformat(),
            }
            for k in result.scalars().all()
        ]
    }


@router.delete("/api-keys/{key_id}", response_model=RevokedResponse)
async def revoke_api_key(key_id: str, db: DB, user: AdminAuth) -> dict:
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.tenant_id == user.tenant_id)
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    key.is_active = False
    return {"revoked": True}
