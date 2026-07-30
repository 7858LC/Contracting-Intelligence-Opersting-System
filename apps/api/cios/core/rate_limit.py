"""Redis-backed fixed-window rate limiting.

rate_limiter() is keyed by client IP, for endpoints that run before any
tenant context exists — this is what stops registration spam and credential
stuffing against /auth/register and /auth/login.

tenant_rate_limiter() is keyed by tenant instead, for authenticated routes
that trigger expensive work downstream (a live Claude call, a Celery task).
Nothing bounded how often a tenant could hit these before — see its
docstring below for why that's a real platform-stress risk, not just a
theoretical one.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request, status

from cios.core.dependencies import Auth
from cios.core.redis import redis_client


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limiter(
    key_prefix: str, max_requests: int, window_seconds: int
) -> Callable[[Request], Awaitable[None]]:
    """FastAPI dependency factory: fixed-window rate limit per client IP.

    Use as a route-level dependency, e.g.:
        dependencies=[Depends(rate_limiter("register", 5, 300))]
    """

    async def _check(request: Request) -> None:
        key = f"ratelimit:{key_prefix}:{_client_ip(request)}"
        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, window_seconds)
        if count > max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )

    return _check


def tenant_rate_limiter(
    key_prefix: str, max_requests: int, window_seconds: int
) -> Callable[[Auth], Awaitable[None]]:
    """FastAPI dependency factory: fixed-window rate limit per tenant.

    V&V Campaign 3 (Platform Stress) finding: nothing bounded how often a
    tenant could trigger the platform's most expensive operations —
    /opportunities/{id}/analyze alone fans out to 6 live Claude calls (the
    CEO Agent plus all 5 Directors), and Award Simulation calls
    claude-opus-4-8 with a 16k max_tokens budget. Production runs exactly
    one Celery worker at concurrency=2 (render.yaml) shared across every
    tenant and every queue (simulations, ingestion, analysis, email,
    pir_scan, research) — a single tenant spamming one of these endpoints
    would starve every other tenant's queued work, on top of unbounded
    Anthropic API cost with no per-tenant cap anywhere in code.

    Use as a route-level dependency, e.g.:
        dependencies=[Depends(tenant_rate_limiter("analyze", 10, 3600))]
    """

    async def _check(user: Auth) -> None:
        key = f"ratelimit:{key_prefix}:tenant:{user.tenant_id}"
        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, window_seconds)
        if count > max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )

    return _check
