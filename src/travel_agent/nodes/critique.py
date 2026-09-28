"""critique 节点：第二视角审查行程。

检查：赶路过多、景点关门、预算超支、重复类型活动、体力过载。
不通过则返回修改建议，回 plan 重排（最多 3 轮，由 graph 条件边控制）。
"""

from __future__ import annotations

import json
import logging

from travel_agent.config import get_settings
from travel_agent.llm import chat, extract_json
from travel_agent.models import Critique
from travel_agent.state import TravelState

logger = logging.getLogger(__name__)

_SYSTEM = """你是旅行行程审查员。审查一份行程的合理性，检查：
1. 赶路过多：单日交通总时长是否过大
2. 景点关门：活动时间是否超出常见开放时间
3. 预算超支：总费用是否超预算
4. 重复类型：连续同类活动是否单调
5. 体力过载：每日活动是否过密

输出 JSON：
{
  "passed": true/false,
  "issues": ["问题1", "问题2"],
  "suggestions": ["建议1", "建议2"]
}
行程可用就 passed=true。只输出 JSON。"""


async def critique(state: TravelState) -> dict:
    """节点：审查行程。"""
    itinerary = state.get("itinerary")
    intent = state.get("intent")
    if not itinerary:
        return {"status": "error", "error": "无行程可审查"}

    s = get_settings()

    user_msg = json.dumps(
        {
            "itinerary": itinerary.model_dump(mode="json"),
            "intent": intent.model_dump(mode="json") if intent else None,
        },
        ensure_ascii=False,
    )

    try:
        text = chat(
            system=_SYSTEM,
            user=user_msg,
            max_tokens=1024,
            model=s.llm_model,
        )
        result = Critique(**extract_json(text))
    except Exception as e:
        logger.exception("critique failed")
        # 审查失败不阻塞，默认通过
        result = Critique(passed=True, issues=[f"审查异常：{e}"])

    return {"critique": result, "status": "presenting" if result.passed else "planning"}
