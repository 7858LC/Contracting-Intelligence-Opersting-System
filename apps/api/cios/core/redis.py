"""Redis client with async support and tenant-namespaced caching."""
import json
from typing import Any

import redis.asyncio as aioredis

from cios.config import settings

redis_client: aioredis.Redis = aioredis.from_url(
    settings.redis_url,
    decode_responses=True,
    encoding="utf-8",
)


class TenantCache:
    """Tenant-isolated cache wrapper."""

    def __init__(self, tenant_id: str, prefix: str = "cios") -> None:
        self.tenant_id = tenant_id
        self.prefix = prefix

    def _key(self, key: str) -> str:
        return f"{self.prefix}:{self.tenant_id}:{key}"

    async def get(self, key: str) -> Any | None:
        raw = await redis_client.get(self._key(key))
        if raw is None:
            return None
        return json.loads(raw)

    async def set(self, key: str, value: Any, ttl: int = settings.redis_cache_ttl) -> None:
        await redis_client.setex(self._key(key), ttl, json.dumps(value, default=str))

    async def delete(self, key: str) -> None:
        await redis_client.delete(self._key(key))

    async def invalidate_pattern(self, pattern: str) -> int:
        keys = await redis_client.keys(self._key(pattern))
        if keys:
            return await redis_client.delete(*keys)
        return 0
