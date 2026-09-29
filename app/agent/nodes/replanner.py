"""replanner 节点：根据用户修改请求调整已有行程。"""

from __future__ import annotations

import json
import logging

from app.agent.llm import chat, extract_json
from app.agent.prompts import REPLANNER_SYSTEM
from app.agent.state import TravelState
from app.common.config import get_settings

logger = logging.getLogger(__name__)


async def replan(state: TravelState) -> dict:
    """节点：修改已有行程。"""
    plan = state.get("current_plan")
    if not plan:
        return {"status": "error", "error": "无行程可修改"}

    s = get_settings()
    iterations = state.get("iterations", 0) + 1

    try:
        text = await chat(
            system=REPLANNER_SYSTEM.format(
                modify_request=state.get("user_message", ""),
                current_plan=json.dumps(plan, ensure_ascii=False),
            ),
            user="请修改行程。",
            max_tokens=8192,
            model=s.planner_model or s.llm_model,
        )
        new_plan = extract_json(text)
    except Exception as e:
        logger.exception("replan failed")
        return {"status": "error", "error": f"行程修改失败：{e}"}

    return {
        "current_plan": new_plan,
        "iterations": iterations,
        "needs_replan": False,
        "status": "validating",
    }
