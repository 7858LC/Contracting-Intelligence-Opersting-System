"""Proves PostgreSQL row-level security actually isolates tenant data at the
database level — a backstop that must hold even if application code forgets
an explicit tenant_id filter. Requires a real, migrated Postgres database.

This exists because RLS policies were previously enabled but never forced
(see migration 007_force_rls): the app connects as the same role that owns
every table it creates via migrations, and Postgres exempts table owners
from RLS unless it's explicitly forced. The policies looked correct and did
nothing. These tests exercise the mechanism directly — setting
app.current_tenant and issuing a deliberately unfiltered query — rather than
going through an endpoint that already adds its own tenant_id filter, which
would pass regardless of whether RLS itself works.
"""

from __future__ import annotations

import os
import uuid

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://cios_user:cios_pass@localhost:5432/cios_test"
)
os.environ.setdefault("JWT_SECRET", "test_secret_minimum_32_characters_long")
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)
os.environ.setdefault("ANTHROPIC_API_KEY", "test_key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")

import pytest
from sqlalchemy import select, text

from cios.core.database import async_session_factory, engine
from cios.models.tenant import Tenant
from cios.models.winning_profile import WPHSolicitation


@pytest.fixture(autouse=True)
async def _fresh_engine_connections_per_test():
    """The engine's pooled connections are bound to whichever event loop first
    used them; pytest-asyncio gives each test (and each test file) its own
    loop, so the pool must be disposed both before (in case an earlier test
    file already bound it to a now-closed loop) and after every test here."""
    await engine.dispose()
    yield
    await engine.dispose()


async def _set_tenant(db, tenant_id: uuid.UUID) -> None:
    await db.execute(
        text("SELECT set_config('app.current_tenant', :t, false)"), {"t": str(tenant_id)}
    )


@pytest.fixture
async def two_tenants_with_data():
    tenant_a = Tenant(name="RLS Test A", slug=f"rls-test-a-{uuid.uuid4().hex[:8]}")
    tenant_b = Tenant(name="RLS Test B", slug=f"rls-test-b-{uuid.uuid4().hex[:8]}")

    async with async_session_factory() as db:
        db.add_all([tenant_a, tenant_b])
        await db.flush()

        await _set_tenant(db, tenant_a.id)
        sol_a = WPHSolicitation(
            tenant_id=tenant_a.id, created_by=uuid.uuid4(), title="Tenant A RLS Test Solicitation"
        )
        db.add(sol_a)
        await db.flush()

        await _set_tenant(db, tenant_b.id)
        sol_b = WPHSolicitation(
            tenant_id=tenant_b.id, created_by=uuid.uuid4(), title="Tenant B RLS Test Solicitation"
        )
        db.add(sol_b)
        await db.flush()
        await db.commit()

    yield tenant_a, tenant_b, sol_a, sol_b

    async with async_session_factory() as db:
        await _set_tenant(db, tenant_a.id)
        await db.execute(text("DELETE FROM wph_solicitations WHERE id = :i"), {"i": str(sol_a.id)})
        await _set_tenant(db, tenant_b.id)
        await db.execute(text("DELETE FROM wph_solicitations WHERE id = :i"), {"i": str(sol_b.id)})
        await db.execute(
            text("DELETE FROM tenants WHERE id IN (:a, :b)"),
            {"a": str(tenant_a.id), "b": str(tenant_b.id)},
        )
        await db.commit()


async def test_rls_hides_other_tenants_rows_with_no_where_clause(two_tenants_with_data):
    """The scenario RLS exists for: application code that forgets the filter."""
    tenant_a, tenant_b, sol_a, sol_b = two_tenants_with_data

    async with async_session_factory() as db:
        await _set_tenant(db, tenant_a.id)
        rows = (await db.execute(select(WPHSolicitation))).scalars().all()
        titles = {r.title for r in rows}

    assert sol_a.title in titles
    assert sol_b.title not in titles


async def test_rls_visibility_follows_tenant_context(two_tenants_with_data):
    tenant_a, tenant_b, sol_a, sol_b = two_tenants_with_data

    async with async_session_factory() as db:
        await _set_tenant(db, tenant_b.id)
        rows = (await db.execute(select(WPHSolicitation))).scalars().all()
        titles = {r.title for r in rows}

    assert sol_b.title in titles
    assert sol_a.title not in titles


async def test_missing_tenant_context_fails_closed(two_tenants_with_data):
    """If app.current_tenant is never set (e.g. a future bug drops it), RLS
    must fail closed — visible to nobody — never fail open."""
    tenant_a, tenant_b, sol_a, sol_b = two_tenants_with_data

    async with async_session_factory() as db:
        await db.execute(text("SELECT set_config('app.current_tenant', '', false)"))
        rows = (await db.execute(select(WPHSolicitation))).scalars().all()
        titles = {r.title for r in rows}

    assert sol_a.title not in titles
    assert sol_b.title not in titles
