"""汇率工具：CNY → 目的地货币。"""

from __future__ import annotations

import logging

import httpx

from travel_agent.cache import cached
from travel_agent.config import get_settings

logger = logging.getLogger(__name__)

# 常见目的地货币（可扩充）
_DEST_CURRENCY = {
    "日本": "JPY", "京都": "JPY", "东京": "JPY", "大阪": "JPY",
    "泰国": "THB", "曼谷": "THB", "清迈": "THB",
    "新加坡": "SGD", "韩国": "KRW", "首尔": "KRW",
    "美国": "USD", "纽约": "USD", "洛杉矶": "USD",
    "欧洲": "EUR", "法国": "EUR", "巴黎": "EUR", "意大利": "EUR", "罗马": "EUR",
    "英国": "GBP", "伦敦": "GBP",
    "澳大利亚": "AUD", "悉尼": "AUD",
}


class ExchangeTool:
    BASE = "https://v6.exchangerate-api.com/v6"

    def __init__(self) -> None:
        self._key = get_settings().exchange_rate_api_key

    @cached(ttl_seconds=3600)
    async def cny_to(self, destination: str) -> float | None:
        """返回 1 CNY 兑目的地货币的汇率。"""
        target = _DEST_CURRENCY.get(destination)
        if not target or target == "CNY":
            return 1.0

        if self._key:
            async with httpx.AsyncClient(timeout=10) as c:
                try:
                    r = await c.get(f"{self.BASE}/{self._key}/pair/CNY/{target}")
                    r.raise_for_status()
                    return r.json().get("conversion_rate")
                except httpx.HTTPError as e:
                    logger.warning("Exchange rate failed: %s", e)

        # 兜底：用 open.er-api.com 免费接口
        async with httpx.AsyncClient(timeout=10) as c:
            try:
                r = await c.get(f"https://open.er-api.com/v6/latest/CNY")
                r.raise_for_status()
                return r.json().get("rates", {}).get(target)
            except httpx.HTTPError as e:
                logger.warning("Fallback exchange rate failed: %s", e)
                return None
