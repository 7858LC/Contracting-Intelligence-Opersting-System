"""Authentication endpoints."""
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select

from cios.core.dependencies import DB, Auth
from cios.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from cios.models.tenant import Tenant, TenantMember

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1)
    company_name: str = Field(..., min_length=1)
    company_slug: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


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


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: DB) -> TokenResponse:
    from python_slugify import slugify

    slug = body.company_slug or slugify(body.company_name)

    existing = await db.execute(select(Tenant).where(Tenant.slug == slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Company slug already taken")

    tenant = Tenant(name=body.company_name, slug=slug, plan="trial")
    db.add(tenant)
    await db.flush()

    user_id = uuid.uuid4()
    member = TenantMember(
        tenant_id=tenant.id,
        user_id=user_id,
        email=body.email,
        full_name=body.full_name,
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


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DB) -> TokenResponse:
    result = await db.execute(
        select(TenantMember).where(TenantMember.email == body.email, TenantMember.is_active == True)  # noqa: E712
    )
    member = result.scalar_one_or_none()

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

    token_payload = {
        "sub": payload["sub"],
        "tenant_id": payload["tenant_id"],
        "email": payload.get("email", ""),
        "role": payload.get("role", "member"),
        "plan": payload.get("plan", "starter"),
    }

    return TokenResponse(
        access_token=create_access_token(token_payload),
        refresh_token=create_refresh_token(token_payload),
        expires_in=3600,
        user_id=payload["sub"],
        tenant_id=payload["tenant_id"],
        role=payload.get("role", "member"),
        plan=payload.get("plan", "starter"),
    )


@router.get("/me")
async def get_me(user: Auth) -> dict:
    return {
        "user_id": str(user.user_id),
        "tenant_id": str(user.tenant_id),
        "email": user.email,
        "role": user.role,
        "plan": user.plan,
    }
