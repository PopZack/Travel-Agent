"""共享 httpx.AsyncClient，复用连接池。"""

from __future__ import annotations

import httpx

_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """获取全局 httpx.AsyncClient 单例。"""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=10)
    return _client


async def close_http_client() -> None:
    """关闭 httpx 客户端，应用停机时调用。"""
    global _client
    if _client:
        await _client.aclose()
        _client = None
