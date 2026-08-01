"""Authentication endpoints."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func, select

from cios.core.dependencies import DB, Auth
from cios.core.rate_limit import rate_limiter
from cios.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from cios.models.tenant import Tenant, TenantInvite, TenantMember

router = APIRouter()

# Unauthenticated endpoints — rate-limited per client IP since there's no
# tenant/user context yet to key off of.
_register_rate_limit = Depends(rate_limiter("register", max_requests=5, window_seconds=300))
_login_rate_limit = Depends(rate_limiter("login", max_requests=10, window_seconds=300))
_accept_invite_rate_limit = Depends(
    rate_limiter("accept_invite", max_requests=5, window_seconds=300)
)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1)
    company_name: str = Field(..., min_length=1)
    company_slug: str | None = None
    # The register form has always collected a "Primary NAICS code" and
    # sent it here — this field just didn't exist, so Pydantic silently
    # dropped it (never a validation error, never persisted) instead of
    # ever reaching Tenant.naics_codes below.
    naics_codes: list[str] = []

    # Nothing normalized email case anywhere in this file (or tenants.py's
    # invite flow) — a user who registered as "Jane@Company.com" and later
    # typed "jane@company.com" at login got rejected with "Invalid
    # credentials", indistinguishable from an actually-wrong password,
    # because the DB lookup was an exact case-sensitive match. Normalizing
    # here means every future row is written lowercase; login's query below
    # also matches case-insensitively so this covers rows already stored
    # with mixed case, not just new ones.
    @field_validator("email", mode="after")
    @classmethod
    def _lowercase_email(cls, v: str) -> str:
        return v.lower()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email", mode="after")
    @classmethod
    def _lowercase_email(cls, v: str) -> str:
        return v.lower()


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    tenant_id: str
    role: str
    plan: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AcceptInviteRequest(BaseModel):
    token: str
    full_name: str = Field(..., min_length=1)
    password: str = Field(..., min_length=8)


class MeResponse(BaseModel):
    user_id: str
    tenant_id: str
    email: str
    role: str
    plan: str


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_register_rate_limit],
)
async def register(body: RegisterRequest, db: DB) -> TokenResponse:
    from slugify import slugify

    slug = body.company_slug or slugify(body.company_name)

    existing = await db.execute(select(Tenant).where(Tenant.slug == slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Company slug already taken")

    tenant = Tenant(name=body.company_name, slug=slug, plan="trial", naics_codes=body.naics_codes)
    db.add(tenant)
    await db.flush()

    user_id = uuid.uuid4()
    member = TenantMember(
        tenant_id=tenant.id,
        user_id=user_id,
        email=body.email,
        full_name=body.full_name,
        password_hash=hash_password(body.password),
        role="owner",
    )
    db.add(member)
    await db.flush()

    token_payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant.id),
        "email": body.email,
        "role": "owner",
        "plan": "trial",
    }

    return TokenResponse(
        access_token=create_access_token(token_payload),
        refresh_token=create_refresh_token(token_payload),
        expires_in=3600,
        user_id=str(user_id),
        tenant_id=str(tenant.id),
        role="owner",
        plan="trial",
    )


@router.post(
    "/accept-invite",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_accept_invite_rate_limit],
)
async def accept_invite(body: AcceptInviteRequest, db: DB) -> TokenResponse:
    """Redeem a TenantInvite token into a real, logged-in TenantMember.

    Previously there was no endpoint for this at all — POST /tenants/members/invite
    created a TenantInvite row and (supposedly) emailed a link, but nothing
    could ever consume that token: an invited teammate had no way to actually
    join, regardless of whether the email arrived.
    """
    result = await db.execute(select(TenantInvite).where(TenantInvite.token == body.token))
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=404, detail="Invalid invite link")

    if invite.accepted_at is not None:
        raise HTTPException(status_code=409, detail="This invite has already been accepted")

    if invite.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=410, detail="This invite has expired")

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == invite.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=403, detail="Workspace is no longer active")

    user_id = uuid.uuid4()
    member = TenantMember(
        tenant_id=invite.tenant_id,
        user_id=user_id,
        email=invite.email,
        full_name=body.full_name,
        password_hash=hash_password(body.password),
        role=invite.role,
    )
    db.add(member)
    invite.accepted_at = datetime.now(UTC)
    await db.flush()

    token_payload = {
        "sub": str(user_id),
        "tenant_id": str(invite.tenant_id),
        "email": invite.email,
        "role": invite.role,
        "plan": tenant.plan,
    }

    return TokenResponse(
        access_token=create_access_token(token_payload),
        refresh_token=create_refresh_token(token_payload),
        expires_in=3600,
        user_id=str(user_id),
        tenant_id=str(invite.tenant_id),
        role=invite.role,
        plan=tenant.plan,
    )


@router.post("/login", response_model=TokenResponse, dependencies=[_login_rate_limit])
async def login(body: LoginRequest, db: DB) -> TokenResponse:
    # TenantMember.email has no unique constraint — case-varying duplicates
    # were always possible at the DB level, but the previous exact-match
    # query never surfaced them as duplicates to *this* query. Matching
    # case-insensitively (added alongside the email-normalization fix) can
    # now legitimately return more than one active row — e.g. someone who
    # hit that exact bug and re-registered with different casing as a
    # workaround. scalar_one_or_none() throws MultipleResultsFound in that
    # case (a 500, live-confirmed), rather than a real "wrong password".
    # Check the submitted password against every match instead of assuming
    # there's exactly one — the password itself is what actually
    # disambiguates which account was meant.
    result = await db.execute(
        select(TenantMember).where(
            func.lower(TenantMember.email) == body.email, TenantMember.is_active == True  # noqa: E712
        )
    )
    candidates = result.scalars().all()
    member = next(
        (
            c
            for c in candidates
            if c.password_hash and verify_password(body.password, c.password_hash)
        ),
        None,
    )
    if not member:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == member.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=403, detail="Account inactive")

    member.last_seen_at = datetime.now(UTC)

    token_payload = {
        "sub": str(member.user_id),
        "tenant_id": str(member.tenant_id),
        "email": member.email,
        "role": member.role,
        "plan": tenant.plan,
    }

    return TokenResponse(
        access_token=create_access_token(token_payload),
        refresh_token=create_refresh_token(token_payload),
        expires_in=3600,
        user_id=str(member.user_id),
        tenant_id=str(member.tenant_id),
        role=member.role,
        plan=tenant.plan,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: DB) -> TokenResponse:
    try:
        payload = decode_token(body.refresh_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")

    # Re-check current DB state rather than trusting the old token's stale
    # claims — refresh tokens live 30 days (settings.jwt_refresh_expiry_days),
    # so without this a landlord suspending a tenant (or removing a member)
    # has no effect on anyone already holding one: they'd silently keep
    # minting fresh access tokens for the token's full lifetime, exactly the
    # same way /login already re-checks tenant.is_active on every new login.
    member_result = await db.execute(
        select(TenantMember).where(
            TenantMember.user_id == uuid.UUID(payload["sub"]),
            TenantMember.is_active == True,  # noqa: E712
        )
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=401, detail="Account inactive")

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == member.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=403, detail="Account inactive")

    token_payload = {
        "sub": str(member.user_id),
        "tenant_id": str(member.tenant_id),
        "email": member.email,
        "role": member.role,
        "plan": tenant.plan,
    }

    return TokenResponse(
        access_token=create_access_token(token_payload),
        refresh_token=create_refresh_token(token_payload),
        expires_in=3600,
        user_id=str(member.user_id),
        tenant_id=str(member.tenant_id),
        role=member.role,
        plan=tenant.plan,
    )


@router.get("/me", response_model=MeResponse)
async def get_me(user: Auth) -> dict:
    return {
        "user_id": str(user.user_id),
        "tenant_id": str(user.tenant_id),
        "email": user.email,
        "role": user.role,
        "plan": user.plan,
    }
