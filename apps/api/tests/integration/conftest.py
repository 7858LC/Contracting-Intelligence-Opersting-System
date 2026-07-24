"""Shared fixtures for integration tests.

These hit a real, migrated Postgres + Redis — see ci.yml's api-test job for
CI, or `docker compose -f infra/docker/docker-compose.yml up postgres redis`
for local dev (same cios_app role setup either way, via
infra/docker/init-scripts/postgres/01-harden-role.sql). Nothing here can run
against a mocked DB; that's the point of this test tier.
"""

from __future__ import annotations

import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://cios_user:cios_pass@localhost:5432/cios_test"
)
os.environ.setdefault("JWT_SECRET", "test_secret_minimum_32_characters_long")
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)
os.environ.setdefault("ANTHROPIC_API_KEY", "test_key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("TENANT_KEY_DERIVATION_SALT", "test_salt")

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
async def _fresh_connections_per_test():
    """The DB engine's and Redis client's pooled connections are bound to
    whichever event loop first used them; pytest-asyncio/anyio give each test
    (and each test file) its own loop, so both must be reset before and
    after every test in this directory — otherwise later tests intermittently
    fail with "Event loop is closed" on whatever connection a prior test left
    bound to its now-dead loop."""
    from cios.core.database import engine
    from cios.core.redis import redis_client

    await engine.dispose()
    await redis_client.aclose()
    yield
    await engine.dispose()
    await redis_client.aclose()


@pytest.fixture
async def client():
    from cios.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
