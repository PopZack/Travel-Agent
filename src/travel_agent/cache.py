"""简单 TTL 缓存。

MVP 用进程内 dict + 时间戳；接口预留 Redis 后端，后续替换无需改调用方。
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

_cache: dict[str, tuple[float, Any]] = {}


def clear() -> None:
    _cache.clear()


def cached(ttl_seconds: float) -> Callable:
    """装饰器：按 (函数名 + 参数) 做键缓存结果，TTL 内命中直接返回。"""

    def decorator(fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = f"{fn.__qualname__}:{args!r}:{kwargs!r}"
            now = time.monotonic()
            if key in _cache:
                exp, val = _cache[key]
                if now < exp:
                    return val
            val = await fn(*args, **kwargs)
            _cache[key] = (now + ttl_seconds, val)
            return val

        return wrapper

    return decorator
