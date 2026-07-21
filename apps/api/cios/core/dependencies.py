"""FastAPI dependency injection — auth, tenant context, pagination."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from cios.core.database import get_db, set_tenant
from cios.core.security import decode_token

bearer = HTTPBearer()


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
) -> CurrentUser:
    try:
        payload = decode_token(credentials.credentials)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No tenant context")

    set_tenant(str(tenant_id))

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
