"""Integration tests for CIOS API health endpoints."""
import pytest
import os
from httpx import AsyncClient, ASGITransport

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://cios_user:cios_pass@localhost:5432/cios_test")
os.environ.setdefault("JWT_SECRET", "test_secret_minimum_32_characters_long")
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)
os.environ.setdefault("ANTHROPIC_API_KEY", "test_key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("TENANT_KEY_DERIVATION_SALT", "test_salt")


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    from cios.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.anyio
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"


@pytest.mark.anyio
async def test_docs_endpoint_available_in_dev(client):
    response = await client.get("/docs")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_unauthorized_access_returns_401(client):
    response = await client.get("/api/v1/opportunities")
    assert response.status_code in (401, 403)


@pytest.mark.anyio
async def test_invalid_token_returns_401(client):
    response = await client.get(
        "/api/v1/opportunities",
        headers={"Authorization": "Bearer invalid_token_here"}
    )
    assert response.status_code == 401
