"""Async PostgreSQL database engine with tenant-aware session management."""

from collections.abc import AsyncGenerator
from contextvars import ContextVar
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from cios.config import settings

_current_tenant: ContextVar[str | None] = ContextVar("current_tenant", default=None)


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
            tenant_id = _current_tenant.get()
            if tenant_id:
                await session.execute(
                    text("SELECT set_config('app.current_tenant', :tenant_id, false)"),
                    {"tenant_id": tenant_id},
                )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def set_tenant(tenant_id: str) -> None:
    _current_tenant.set(tenant_id)


def get_tenant() -> str | None:
    return _current_tenant.get()
