"""Unhandled backend exceptions must still return real 500 responses with
CORS headers intact, not the "blocked by CORS policy" browser error that
actually meant a 500 with no headers.

Before cios/main.py's request_timing middleware wrapped call_next() in a
try/except, a raw (non-HTTPException) error raised inside a route escaped
all the way to Starlette's outer, framework-level ServerErrorMiddleware,
whose generic 500 never passes back through CORSMiddleware's header-adding
logic. Two real incidents were reported as CORS failures that were actually
this: TenantVectorStore.search() calling a removed Qdrant client method,
and (suspected) an S3 misconfiguration on the upload endpoint.

Note this can't be fixed with a plain `@app.exception_handler(Exception)`:
Starlette's BaseHTTPMiddleware (what `@app.middleware("http")` is) always
re-raises the exception it captured from call_next()'s inner task, even
after an app-level handler already built and sent a real response for it
(see starlette/middleware/base.py's call_next, `raise app_exc from ...`) —
confirmed empirically, not by documentation alone. The fix has two parts:
catch the exception where it actually resurfaces (inside request_timing),
and register CORSMiddleware *after* request_timing so it wraps it and can
still attach headers to the fallback response built in that except block.
This test reproduces the mechanism directly rather than pinning it to
either specific bug.
"""

from __future__ import annotations

import random
import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

ALLOWED_ORIGIN = "http://localhost:3000"


def _fake_client_ip() -> str:
    return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


async def _register(client: AsyncClient) -> dict:
    suffix = uuid.uuid4().hex[:10]
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"exc-handler-{suffix}@example.com",
            "password": "SmokeTest123!",
            "full_name": "Exception Handler Test",
            "company_name": f"Exc Handler Co {suffix}",
        },
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.mark.anyio
async def test_unhandled_exception_returns_500_with_cors_headers(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    """The exact failure mode reported: a raw exception inside a route must
    surface as a normal 500 with CORS headers, not a bare connection-style
    failure with none."""
    monkeypatch.setattr(
        "cios.vector.tenant_store.TenantVectorStore.search",
        AsyncMock(side_effect=RuntimeError("simulated unhandled backend error")),
    )
    headers = await _register(client)
    headers["Origin"] = ALLOWED_ORIGIN

    resp = await client.post(
        "/api/v1/knowledge-vault/search",
        headers=headers,
        json={"query": "anything"},
    )

    assert resp.status_code == 500, resp.text
    assert resp.json() == {"detail": "Internal server error"}
    assert resp.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN


@pytest.mark.anyio
async def test_ordinary_http_exceptions_still_carry_cors_headers(client: AsyncClient):
    """No regression check: a normal, intentional HTTPException (never
    routed through the new catch-all) must keep behaving exactly as before —
    real status code, real CORS headers."""
    owner_headers = await _register(client)
    other_headers = await _register(client)
    other_headers["Origin"] = ALLOWED_ORIGIN

    upload = await client.post(
        "/api/v1/knowledge-vault/upload",
        headers=owner_headers,
        files={"file": ("private.txt", b"secret", "text/plain")},
        data={"document_type": "general", "attestation": "true"},
    )
    document_id = upload.json()["document_id"]

    resp = await client.get(
        f"/api/v1/knowledge-vault/{document_id}/download", headers=other_headers
    )

    assert resp.status_code == 404, resp.text
    assert resp.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN
