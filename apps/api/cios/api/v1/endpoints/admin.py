"""Landlord/platform-operator API — the tenant-ops layer.

Authenticated by real, per-person ``PlatformAdmin`` accounts (see
``cios/models/tenant.py``), never by a shared secret. Deliberately a separate
JWT audience from tenant auth (the ``scope: platform_admin`` claim) — see
``cios/core/dependencies.py`` for why the two must never be interchangeable.

Every tenant-scoped table is RLS-forced (migration 007), so a landlord query
that needs a specific tenant's usage numbers has to explicitly scope into that
tenant the same way a tenant request would — there is no bypass. Every ops
action (suspend/activate) writes an ``AuditLog`` row attributed to the acting
landlord, in the affected tenant's own audit trail.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from cios.core.dependencies import DB, Pages, PlatformAuth, PlatformOperatorAuth
from cios.core.rate_limit import rate_limiter
from cios.core.security import create_access_token, create_refresh_token, verify_password
from cios.models.opportunity import Opportunity
from cios.models.subscription import Subscription
from cios.models.tenant import AuditLog, PlatformAdmin, Tenant, TenantMember
from cios.models.winning_profile import WPHSolicitation

router = APIRouter()

_admin_login_rate_limit = Depends(rate_limiter("admin_login", max_requests=10, window_seconds=300))


# ── Auth ─────────────────────────────────────────────────────────────────────


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    admin_id: str
    email: str
    full_name: str
    role: str


@router.post(
    "/auth/login", response_model=AdminTokenResponse, dependencies=[_admin_login_rate_limit]
)
async def admin_login(body: AdminLoginRequest, db: DB) -> AdminTokenResponse:
    result = await db.execute(
        select(PlatformAdmin).where(
            PlatformAdmin.email == body.email, PlatformAdmin.is_active == True  # noqa: E712
        )
    )
    admin = result.scalar_one_or_none()
    if not admin or not verify_password(body.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    admin.last_seen_at = datetime.now(UTC)

    token_payload = {
        "sub": str(admin.id),
        "scope": "platform_admin",
        "email": admin.email,
        "full_name": admin.full_name,
        "role": admin.role,
    }
    return AdminTokenResponse(
        access_token=create_access_token(token_payload),
        refresh_token=create_refresh_token(token_payload),
        expires_in=3600,
        admin_id=str(admin.id),
        email=admin.email,
        full_name=admin.full_name,
        role=admin.role,
    )


@router.get("/auth/me", response_model=dict)
async def admin_me(admin: PlatformAuth) -> dict:
    return {
        "admin_id": str(admin.admin_id),
        "email": admin.email,
        "full_name": admin.full_name,
        "role": admin.role,
    }


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _scope_to_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Set the RLS session GUC for one query. tenant_members/subscriptions/
    audit_logs carry no RLS policy (see 007_force_rls) so they're readable
    platform-wide without this; opportunities/wph_* etc. do require it.

    ``false`` (session-level, not SET LOCAL) — see the identical tradeoff
    note on get_current_user in core/dependencies.py: SET LOCAL clears on
    every commit, which breaks handlers here that commit mid-request
    (suspend/activate). Safe because every landlord request re-sets this
    before touching an RLS-scoped table."""
    await db.execute(
        text("SELECT set_config('app.current_tenant', :tenant_id, false)"),
        {"tenant_id": str(tenant_id)},
    )


async def _get_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> Tenant:
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


async def _write_audit(
    db: AsyncSession, tenant_id: uuid.UUID, admin: PlatformOperatorAuth, action: str
) -> None:
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            user_id=None,
            action=action,
            resource_type="tenant",
            resource_id=str(tenant_id),
            extra_metadata={
                "actor": "platform_admin",
                "platform_admin_id": str(admin.admin_id),
                "platform_admin_email": admin.email,
            },
        )
    )


# ── Platform stats ───────────────────────────────────────────────────────────


@router.get("/stats", response_model=dict)
async def platform_stats(db: DB, admin: PlatformAuth) -> dict:
    tenant_count = (await db.execute(select(func.count(Tenant.id)))).scalar_one()
    active_tenant_count = (
        await db.execute(select(func.count(Tenant.id)).where(Tenant.is_active == True))  # noqa: E712
    ).scalar_one()
    active_subs = (
        await db.execute(select(func.count(Subscription.id)).where(Subscription.status == "active"))
    ).scalar_one()
    member_count = (await db.execute(select(func.count(TenantMember.id)))).scalar_one()

    return {
        "tenants": tenant_count,
        "active_tenants": active_tenant_count,
        "active_subscriptions": active_subs,
        "total_members": member_count,
        "platform_version": "1.0.0",
    }


# ── Tenants ──────────────────────────────────────────────────────────────────


@router.get("/tenants", response_model=dict)
async def list_all_tenants(
    db: DB,
    admin: PlatformAuth,
    pages: Pages,
    q: str | None = Query(None, description="Search name/slug"),
) -> dict:
    query = select(Tenant).order_by(Tenant.created_at.desc())
    if q:
        query = query.where(Tenant.name.ilike(f"%{q}%") | Tenant.slug.ilike(f"%{q}%"))

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    rows = (await db.execute(query.offset(pages.offset).limit(pages.limit))).scalars().all()

    # Unscoped tables (no RLS) — safe to join across tenants without per-row scoping.
    tenant_ids = [t.id for t in rows]
    member_counts: dict[uuid.UUID, int] = {}
    if tenant_ids:
        member_rows = await db.execute(
            select(TenantMember.tenant_id, func.count(TenantMember.id))
            .where(TenantMember.tenant_id.in_(tenant_ids), TenantMember.is_active == True)  # noqa: E712
            .group_by(TenantMember.tenant_id)
        )
        member_counts = dict(member_rows.all())

    return {
        "items": [
            {
                "id": str(t.id),
                "name": t.name,
                "slug": t.slug,
                "plan": t.plan,
                "is_active": t.is_active,
                "member_count": member_counts.get(t.id, 0),
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in rows
        ],
        "total": total,
        "page": pages.page,
        "page_size": pages.page_size,
    }


@router.get("/tenants/{tenant_id}", response_model=dict)
async def get_tenant_detail(tenant_id: uuid.UUID, db: DB, admin: PlatformAuth) -> dict:
    tenant = await _get_tenant(db, tenant_id)

    members = (
        (
            await db.execute(
                select(TenantMember)
                .where(TenantMember.tenant_id == tenant_id)
                .order_by(TenantMember.created_at)
            )
        )
        .scalars()
        .all()
    )
    subscription = (
        await db.execute(select(Subscription).where(Subscription.tenant_id == tenant_id))
    ).scalar_one_or_none()

    # RLS-forced tables — must scope into this one tenant to see its rows.
    await _scope_to_tenant(db, tenant_id)
    opportunity_count = (
        await db.execute(
            select(func.count(Opportunity.id)).where(Opportunity.tenant_id == tenant_id)
        )
    ).scalar_one()
    solicitation_count = (
        await db.execute(
            select(func.count(WPHSolicitation.id)).where(WPHSolicitation.tenant_id == tenant_id)
        )
    ).scalar_one()

    last_seen = max((m.last_seen_at for m in members if m.last_seen_at), default=None)

    return {
        "tenant": tenant.to_dict(),
        "usage": {
            "member_count": len([m for m in members if m.is_active]),
            "opportunity_count": opportunity_count,
            "solicitation_count": solicitation_count,
            "last_activity_at": last_seen.isoformat() if last_seen else None,
        },
        "subscription": (
            {
                "plan": subscription.plan,
                "status": subscription.status,
                "current_period_end": (
                    subscription.current_period_end.isoformat()
                    if subscription.current_period_end
                    else None
                ),
            }
            if subscription
            else None
        ),
        "members": [
            {
                "id": str(m.id),
                "email": m.email,
                "full_name": m.full_name,
                "role": m.role,
                "is_active": m.is_active,
                "last_seen_at": m.last_seen_at.isoformat() if m.last_seen_at else None,
            }
            for m in members
        ],
    }


@router.post("/tenants/{tenant_id}/suspend", response_model=dict)
async def suspend_tenant(tenant_id: uuid.UUID, db: DB, admin: PlatformOperatorAuth) -> dict:
    tenant = await _get_tenant(db, tenant_id)
    if not tenant.is_active:
        return {"id": str(tenant.id), "is_active": False}
    tenant.is_active = False
    await _write_audit(db, tenant_id, admin, "tenant.suspended")
    await db.commit()
    return {"id": str(tenant.id), "is_active": False}


@router.post("/tenants/{tenant_id}/activate", response_model=dict)
async def activate_tenant(tenant_id: uuid.UUID, db: DB, admin: PlatformOperatorAuth) -> dict:
    tenant = await _get_tenant(db, tenant_id)
    if tenant.is_active:
        return {"id": str(tenant.id), "is_active": True}
    tenant.is_active = True
    await _write_audit(db, tenant_id, admin, "tenant.activated")
    await db.commit()
    return {"id": str(tenant.id), "is_active": True}


@router.post("/tenants/{tenant_id}/council/grant", response_model=dict)
async def grant_council_membership(
    tenant_id: uuid.UUID, db: DB, admin: PlatformOperatorAuth
) -> dict:
    tenant = await _get_tenant(db, tenant_id)
    if tenant.is_council_member:
        return {"id": str(tenant.id), "is_council_member": True}
    tenant.is_council_member = True
    await _write_audit(db, tenant_id, admin, "tenant.council_membership_granted")
    await db.commit()
    return {"id": str(tenant.id), "is_council_member": True}


@router.post("/tenants/{tenant_id}/council/revoke", response_model=dict)
async def revoke_council_membership(
    tenant_id: uuid.UUID, db: DB, admin: PlatformOperatorAuth
) -> dict:
    tenant = await _get_tenant(db, tenant_id)
    if not tenant.is_council_member:
        return {"id": str(tenant.id), "is_council_member": False}
    tenant.is_council_member = False
    await _write_audit(db, tenant_id, admin, "tenant.council_membership_revoked")
    await db.commit()
    return {"id": str(tenant.id), "is_council_member": False}


@router.get("/tenants/{tenant_id}/audit-log", response_model=dict)
async def tenant_audit_log(tenant_id: uuid.UUID, db: DB, admin: PlatformAuth, pages: Pages) -> dict:
    await _get_tenant(db, tenant_id)
    query = (
        select(AuditLog)
        .where(AuditLog.tenant_id == tenant_id)
        .order_by(AuditLog.created_at.desc())
    )
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    rows = (await db.execute(query.offset(pages.offset).limit(pages.limit))).scalars().all()
    return {
        "items": [
            {
                "id": str(a.id),
                "action": a.action,
                "resource_type": a.resource_type,
                "resource_id": a.resource_id,
                "extra_metadata": a.extra_metadata,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in rows
        ],
        "total": total,
        "page": pages.page,
        "page_size": pages.page_size,
    }
