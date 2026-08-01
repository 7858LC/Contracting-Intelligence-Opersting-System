"""FastAPI dependency injection — auth, tenant context, pagination."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from cios.core.database import get_db
from cios.core.features import plan_has_feature
from cios.core.security import decode_token

bearer = HTTPBearer()

# Not the ``DB`` alias below (defined later, so route signatures can order
# ``db``/``user`` params however they like) — this is the *same* Depends(get_db)
# callable, so FastAPI's per-request dependency cache resolves it once and
# reuses the identical AsyncSession object everywhere it's requested in the
# same request, including here.
_DBDep = Annotated[AsyncSession, Depends(get_db)]


class CurrentUser:
    def __init__(self, user_id: UUID, tenant_id: UUID, email: str, role: str, plan: str):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.email = email
        self.role = role
        self.plan = plan

    @property
    def is_admin(self) -> bool:
        return self.role in ("admin", "owner")

    @property
    def is_enterprise(self) -> bool:
        return self.plan == "enterprise"


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
    db: _DBDep,
) -> CurrentUser:
    try:
        payload = decode_token(credentials.credentials)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No tenant context")

    # Set the RLS session GUC directly on the session every route handler will
    # actually use (FastAPI caches Depends(get_db) per request, so this is the
    # same AsyncSession the endpoint's own `db: DB` parameter resolves to,
    # regardless of where `db`/`user` fall in that endpoint's parameter list).
    # Previously this went through a ContextVar (`set_tenant`) read inside
    # get_db() at session-creation time — correct only when get_db() happened
    # to resolve *after* get_current_user, which FastAPI resolves dependencies
    # strictly in parameter declaration order, so any route with `db: DB`
    # listed before `user: Auth` silently ran with no tenant context set at
    # all.
    #
    # `false` (session-level, not SET LOCAL): several service layers in this
    # codebase (WPHService, PIRCompany creation) call db.commit() mid-request
    # and keep using the same session afterward — SET LOCAL clears at every
    # commit, which broke every RLS-scoped statement issued after the first
    # commit in a request (tried it, it's a real regression — don't reuse
    # that approach here). `false` persists for the life of the pooled
    # physical connection instead, which sounds like it risks a stale tenant
    # leaking into a future request on the same connection — but it doesn't
    # in practice: this line runs, unconditionally, at the start of every
    # authenticated request (parameter order no longer matters), so whatever
    # the connection carried in gets overwritten with the correct tenant
    # before any endpoint code, or any RLS-scoped query, runs.
    await db.execute(
        text("SELECT set_config('app.current_tenant', :tenant_id, false)"),
        {"tenant_id": str(tenant_id)},
    )

    return CurrentUser(
        user_id=UUID(payload["sub"]),
        tenant_id=UUID(tenant_id),
        email=payload.get("email", ""),
        role=payload.get("role", "member"),
        plan=payload.get("plan", "starter"),
    )


async def require_admin(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return user


def require_feature(feature: str):
    """Router-level gate: 403s any request whose tenant plan doesn't include
    ``feature`` (see core/features.py for the plan->feature table). Apply via
    ``include_router(..., dependencies=[Depends(require_feature("x"))])`` so
    it covers every route under that prefix, not just one — Competitive
    Intelligence, Capabilities & Gaps, Teaming, and Award Simulator are each
    sold as a whole module on the pricing page, not per-endpoint."""

    async def _check(user: Annotated[CurrentUser, Depends(get_current_user)]) -> None:
        if not plan_has_feature(user.plan, feature):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Your current plan does not include {feature.replace('_', ' ')}. "
                "Upgrade your subscription to access this feature.",
            )

    return _check


class CurrentPlatformAdmin:
    """A landlord/platform-operator identity — never a tenant, never RLS-scoped
    by default. Distinct from ``CurrentUser`` on purpose: the two must never be
    interchangeable, so a leaked tenant token can't be replayed as landlord
    access or vice versa."""

    def __init__(self, admin_id: UUID, email: str, full_name: str, role: str):
        self.admin_id = admin_id
        self.email = email
        self.full_name = full_name
        self.role = role

    @property
    def can_operate(self) -> bool:
        """Read-only "support" role vs. "admin" role, which can also take tenant
        ops actions (suspend/activate)."""
        return self.role == "admin"


async def get_current_platform_admin(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
) -> CurrentPlatformAdmin:
    try:
        payload = decode_token(credentials.credentials)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    # The claim that separates this audience from tenant-user tokens — a tenant
    # token never carries it, and a landlord token never carries tenant_id.
    if payload.get("scope") != "platform_admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not a landlord token")

    return CurrentPlatformAdmin(
        admin_id=UUID(payload["sub"]),
        email=payload.get("email", ""),
        full_name=payload.get("full_name", ""),
        role=payload.get("role", "support"),
    )


async def require_platform_operator(
    admin: Annotated[CurrentPlatformAdmin, Depends(get_current_platform_admin)],
) -> CurrentPlatformAdmin:
    if not admin.can_operate:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Landlord operator role required"
        )
    return admin


class Pagination:
    def __init__(self, page: int = 1, page_size: int = 25) -> None:
        if page < 1:
            raise HTTPException(status_code=400, detail="page must be >= 1")
        if page_size < 1 or page_size > 100:
            raise HTTPException(status_code=400, detail="page_size must be 1–100")
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size

    @property
    def limit(self) -> int:
        return self.page_size


# Type aliases
DB = Annotated[AsyncSession, Depends(get_db)]
Auth = Annotated[CurrentUser, Depends(get_current_user)]
AdminAuth = Annotated[CurrentUser, Depends(require_admin)]
Pages = Annotated[Pagination, Depends()]

# Landlord/platform-operator auth — separate audience from tenant Auth/AdminAuth above.
PlatformAuth = Annotated[CurrentPlatformAdmin, Depends(get_current_platform_admin)]
PlatformOperatorAuth = Annotated[CurrentPlatformAdmin, Depends(require_platform_operator)]
