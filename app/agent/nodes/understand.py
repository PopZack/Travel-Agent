"""understand_request 节点：LLM 从用户消息提取 intent + slot。"""

from __future__ import annotations

import json
import logging
from datetime import date

from app.agent.llm import chat, extract_json
from app.agent.prompts import UNDERSTAND_SYSTEM
from app.agent.state import TravelState

logger = logging.getLogger(__name__)


async def understand_request(state: TravelState) -> dict:
    """节点：理解用户意图，提取结构化参数。"""
    user_msg = state["user_message"]
    today = date.today().isoformat()

    # 把对话历史拼进 user 消息，让 LLM 理解上下文
    history = state.get("messages", [])
    if history:
        history_text = "\n".join(f"{m['role']}: {m['content']}" for m in history[-6:])
        user_content = f"对话历史：\n{history_text}\n\n当前用户消息：{user_msg}"
    else:
        user_content = user_msg

    try:
        text = await chat(
            system=UNDERSTAND_SYSTEM.format(today=today),
            user=user_content,
            max_tokens=1024,
        )
        data = extract_json(text)
    except Exception as e:
        logger.exception("understand_request failed")
        return {"status": "error", "error": f"意图理解失败：{e}"}

    return {
        "intent": data.get("intent", "general_chat"),
        "destination": data.get("destination"),
        "start_date": data.get("start_date"),
        "end_date": data.get("end_date"),
        "days": data.get("days"),
        "travelers": data.get("travelers"),
        "budget": data.get("budget"),
        "preferences": data.get("preferences", []),
        "status": "checking",
    }
