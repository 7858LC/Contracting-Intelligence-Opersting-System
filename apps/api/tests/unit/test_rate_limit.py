"""Tests for the Redis-backed rate limiter guarding /auth/register and /auth/login."""

from __future__ import annotations

import os
import uuid

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://cios_user:cios_pass@localhost/x")
os.environ.setdefault("JWT_SECRET", "test_secret_minimum_32_characters_long")
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)
os.environ.setdefault("ANTHROPIC_API_KEY", "test_key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from cios.core.rate_limit import rate_limiter
from cios.core.redis import redis_client


def _request(ip: str, forwarded_for: str | None = None) -> Request:
    headers = [(b"x-forwarded-for", forwarded_for.encode())] if forwarded_for else []
    return Request({"type": "http", "client": (ip, 1234), "headers": headers})


def _prefix() -> str:
    return f"test-{uuid.uuid4().hex[:8]}"


@pytest.fixture(autouse=True)
async def _fresh_redis_connection_per_test():
    """redis_client is a module-level singleton bound to whichever event loop
    first used it; pytest-asyncio gives each test its own loop, so the pooled
    connection must be closed after every test or the next one hits a stale,
    closed loop ("Event loop is closed")."""
    yield
    await redis_client.aclose()


async def test_allows_requests_under_the_limit():
    prefix = _prefix()
    check = rate_limiter(prefix, max_requests=3, window_seconds=60)
    req = _request("10.0.0.1")
    try:
        for _ in range(3):
            await check(req)  # should not raise
    finally:
        await redis_client.delete(f"ratelimit:{prefix}:10.0.0.1")


async def test_blocks_once_the_limit_is_exceeded():
    prefix = _prefix()
    check = rate_limiter(prefix, max_requests=3, window_seconds=60)
    req = _request("10.0.0.2")
    try:
        for _ in range(3):
            await check(req)
        with pytest.raises(HTTPException) as exc_info:
            await check(req)
        assert exc_info.value.status_code == 429
    finally:
        await redis_client.delete(f"ratelimit:{prefix}:10.0.0.2")


async def test_limit_is_tracked_independently_per_ip():
    prefix = _prefix()
    check = rate_limiter(prefix, max_requests=1, window_seconds=60)
    req_a, req_b = _request("10.0.0.3"), _request("10.0.0.4")
    try:
        await check(req_a)  # ok
        await check(req_b)  # ok — different IP, independent counter
        with pytest.raises(HTTPException):
            await check(req_a)
    finally:
        await redis_client.delete(f"ratelimit:{prefix}:10.0.0.3", f"ratelimit:{prefix}:10.0.0.4")


async def test_honors_x_forwarded_for_ahead_of_socket_ip():
    """Behind a load balancer (Fly/Render/ALB), request.client.host is the proxy,
    not the real client — the limiter must key off X-Forwarded-For when present."""
    prefix = _prefix()
    check = rate_limiter(prefix, max_requests=1, window_seconds=60)
    req = _request("127.0.0.1", forwarded_for="9.9.9.9, 127.0.0.1")
    try:
        await check(req)
        with pytest.raises(HTTPException):
            await check(req)
    finally:
        await redis_client.delete(f"ratelimit:{prefix}:9.9.9.9")
