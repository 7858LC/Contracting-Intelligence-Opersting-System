"""Async PostgreSQL database engine + session management.

Tenant RLS context (``app.current_tenant``) is deliberately *not* set here.
It used to be applied via a ``ContextVar`` read at session-creation time —
correct only when that ContextVar happened to already be set by the time
this ran, which depended on FastAPI resolving a *different* dependency
(``get_current_user``) first. FastAPI resolves dependencies strictly in a
route's parameter declaration order, so any route listing ``db: DB`` before
``user: Auth`` silently opened a session with no tenant context at all, and
—because the underlying Postgres session-level GUC isn't reset when
SQLAlchemy's pool checks a physical connection back in — could inherit
whatever tenant a *previous, different* request last set on that pooled
connection. See ``core/dependencies.py``'s ``get_current_user`` for the
fix: it now sets the GUC directly (as ``SET LOCAL``, transaction-scoped) on
the exact same cached session the route handler receives, independent of
parameter order.
"""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from cios.config import settings


class Base(DeclarativeBase):
    """Base model class with common fields."""

    def to_dict(self) -> dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


engine: AsyncEngine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.debug,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
