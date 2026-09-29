"""response 节点：生成最终回复。

有行程 → 总结行程；无行程（闲聊/天气查询等）→ 直接 LLM 回复。
"""

from __future__ import annotations

import json
import logging

from app.agent.llm import chat
from app.agent.prompts import RESPONSE_SYSTEM
from app.agent.state import TravelState

logger = logging.getLogger(__name__)

_CHAT_SYSTEM = """你是旅行助手，友好地回应用户。

根据对话历史和当前消息自然地回应。如果用户闲聊就聊天，问推荐就推荐，问问题就回答。
回复简洁自然，不要重复之前说过的内容。"""


async def final_response(state: TravelState) -> dict:
    """节点：生成自然语言回复。"""
    plan = state.get("current_plan")

    # 有行程 → 总结行程
    if plan and plan.get("days"):
        try:
            response = await chat(
                system=RESPONSE_SYSTEM.format(plan=json.dumps(plan, ensure_ascii=False)),
                user="请生成回复。",
                max_tokens=512,
            )
        except Exception as e:
            logger.exception("final_response plan summary failed")
            total = plan.get("total_cost", 0)
            days = len(plan.get("days", []))
            response = f"已为您规划好{days}天行程，总费用约{total:.0f}元。"
        return {"response": response, "status": "done"}

    # 无行程 → 闲聊/通用回复（带对话历史）
    user_msg = state.get("user_message", "")
    history = state.get("messages", [])

    # 拼对话历史
    if history:
        history_text = "\n".join(f"{m['role']}: {m['content']}" for m in history[-6:])
        user_content = f"对话历史：\n{history_text}\n\n当前用户消息：{user_msg}"
    else:
        user_content = user_msg

    try:
        response = await chat(
            system=_CHAT_SYSTEM,
            user=user_content,
            max_tokens=512,
        )
    except Exception as e:
        logger.exception("final_response chat failed")
        response = ""

    if not response.strip():
        response = "你好！我是旅行助手，可以帮你规划行程。告诉我你想去哪里、玩几天、预算多少就行。"

    return {"response": response, "status": "done"}
