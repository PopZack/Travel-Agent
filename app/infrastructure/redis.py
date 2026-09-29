"""Redis 客户端（可选）。

未配置 redis_url 时用内存 dict 兜底，接口一致。
"""

from __future__ import annotations

import json
from typing import Any


class InMemoryRedis:
    """内存 dict 兜底，实现 get/set/delete 接口。"""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._store[key] = value

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def get_json(self, key: str) -> Any | None:
        val = await self.get(key)
        return json.loads(val) if val else None

    async def set_json(self, key: str, value: Any, ex: int | None = None) -> None:
        await self.set(key, json.dumps(value, ensure_ascii=False), ex)


class RedisClient(InMemoryRedis):
    """真实 Redis 客户端。"""

    def __init__(self, url: str) -> None:
        import redis.asyncio as aioredis

        self._redis = aioredis.from_url(url)

    async def get(self, key: str) -> str | None:
        return await self._redis.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        await self._redis.set(key, value, ex=ex)

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)


def get_redis() -> InMemoryRedis:
    """获取 Redis 客户端单例。未配置则用内存兜底。"""
    global _redis_client
    if _redis_client is None:
        from app.common.config import get_settings

        url = get_settings().redis_url
        if url:
            _redis_client = RedisClient(url)
        else:
            _redis_client = InMemoryRedis()
    return _redis_client


_redis_client: InMemoryRedis | None = None
