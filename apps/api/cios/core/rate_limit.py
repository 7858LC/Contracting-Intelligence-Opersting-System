"""Redis-backed fixed-window rate limiting for unauthenticated endpoints.

Keyed by client IP rather than tenant, since these endpoints run before any
tenant context exists — this is what stops registration spam and credential
stuffing against /auth/register and /auth/login.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request, status

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
