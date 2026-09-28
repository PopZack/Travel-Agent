"""parse_intent 节点：用 LLM 从自然语言抽取结构化意图。"""

from __future__ import annotations

import logging

from travel_agent.config import get_settings
from travel_agent.llm import chat, extract_json
from travel_agent.models import ParsedIntent, TravelStyle
from travel_agent.state import TravelState

logger = logging.getLogger(__name__)

_SYSTEM = """你是旅行需求解析器。从用户描述抽取结构化意图，输出严格 JSON。

字段：
- destination: 目的地
- start_date: ISO 日期 YYYY-MM-DD（"11月初"→该月1号或2号，用今天日期推算）
- end_date: ISO 日期（start_date + days - 1）
- days: 天数
- adults: 成人数（默认1）
- children: 儿童数（默认0，"带爸妈"→adults=3）
- budget_cny: 总预算人民币（"1.5万"→15000）
- styles: 从 [culture,nature,food,family,budget,luxury,adventure] 选
- notes: 其他偏好

注意："带爸妈"表示 adults=3（用户+父母两人）。只输出JSON。今天日期：{today}。"""


async def parse_intent(state: TravelState) -> dict:
    """节点：解析用户意图。"""
    s = get_settings()
    query = state["user_query"]
    today = state.get("intent_today", "")  # 由 UI 注入；否则用系统日期
    if not today:
        from datetime import date as _d

        today = _d.today().isoformat()

    try:
        text = chat(
            system=_SYSTEM.format(today=today),
            user=query,
            max_tokens=1024,
            model=s.llm_model,
        )
        data = extract_json(text)
        # 枚举校验
        raw_styles = data.get("styles", [])
        data["styles"] = [
            TravelStyle(x) for x in raw_styles if x in {e.value for e in TravelStyle}
        ]
        intent = ParsedIntent(**data)
    except Exception as e:
        logger.exception("parse_intent failed")
        return {"status": "error", "error": f"意图解析失败：{e}"}

    return {"intent": intent, "status": "researching"}
