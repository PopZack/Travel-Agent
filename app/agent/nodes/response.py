"""response 节点：生成最终回复，保存行程。"""

from __future__ import annotations

import json
import logging

from app.agent.llm import chat
from app.agent.prompts import RESPONSE_SYSTEM
from app.agent.state import TravelState

logger = logging.getLogger(__name__)


async def final_response(state: TravelState) -> dict:
    """节点：生成自然语言回复。"""
    plan = state.get("current_plan")
    if not plan:
        return {"response": "抱歉，无法生成行程。", "status": "done"}

    try:
        response = await chat(
            system=RESPONSE_SYSTEM.format(plan=json.dumps(plan, ensure_ascii=False)),
            user="请生成回复。",
            max_tokens=512,
        )
    except Exception as e:
        logger.exception("final_response failed")
        # 兜底：简单总结
        total = plan.get("total_cost", 0)
        days = len(plan.get("days", []))
        response = f"已为您规划好{days}天行程，总费用约{total:.0f}元。"

    return {"response": response, "status": "done"}
