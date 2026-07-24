"""Integration tests for CIOS API health endpoints."""

import pytest


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
        "/api/v1/opportunities", headers={"Authorization": "Bearer invalid_token_here"}
    )
    assert response.status_code == 401
