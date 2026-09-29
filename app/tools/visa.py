"""签证信息工具：基于 Wikidata 的启发式查询。

MVP 用静态规则表 + 少量 Wikidata SPARQL；后续可接正式签证 API。
"""

from __future__ import annotations

import logging

import httpx

from app.tools.cache import cached

logger = logging.getLogger(__name__)

# 中国护照 → 目的地 签证情况（简化表，实际应查官方）
_VISA_TABLE = {
    "日本": "需签证（单次/多次旅游签）",
    "泰国": "免签（2024.3 起永久免签，停留 30 天）",
    "新加坡": "免签（停留 30 天）",
    "韩国": "需签证（或济州岛免签 30 天）",
    "美国": "需签证（B1/B2）",
    "法国": "申根签证",
    "意大利": "申根签证",
    "英国": "需签证（Standard Visitor）",
    "澳大利亚": "需签证（600 类）",
}


class VisaTool:
    @cached(ttl_seconds=86400 * 7)  # 签证政策 7 天缓存
    async def lookup(self, destination: str, passport_country: str = "中国") -> str:
        """查签证要求。先查本地表，miss 时回退到 Wikidata。"""
        if passport_country == "中国":
            if destination in _VISA_TABLE:
                return _VISA_TABLE[destination]

        # 回退：Wikidata SPARQL（简化，实际查询需构造正确的关系）
        return await self._wikidata_fallback(destination, passport_country)

    async def _wikidata_fallback(self, destination: str, passport: str) -> str:
        """占位：用 Wikidata 查 visaRequired / visaFree 关系。

        完整实现需映射国名到 QID 并构造 SPARQL；MVP 先返回提示。
        """
        return f"建议查询官方签证政策：{passport} 护照前往 {destination}"
