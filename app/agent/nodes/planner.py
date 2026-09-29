"""planner 节点：LLM 根据工具结果生成结构化行程。"""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta

from app.agent.llm import chat, extract_json
from app.agent.prompts import PLANNER_SYSTEM
from app.agent.state import TravelState
from app.common.config import get_settings

logger = logging.getLogger(__name__)


async def plan_trip(state: TravelState) -> dict:
    """节点：编排行程。"""
    destination = state.get("destination")
    if not destination:
        return {"status": "error", "error": "缺少目的地"}

    s = get_settings()

    # 推算日期
    start = state.get("start_date")
    if start:
        start = date.fromisoformat(start)
    else:
        start = date.today() + timedelta(days=30)

    days = state.get("days") or 4

    # 工具结果
    tool_results = state.get("tool_results", [])
    research_data = tool_results[-1] if tool_results else None

    user_msg = json.dumps(
        {
            "destination": destination,
            "days": days,
            "start_date": start.isoformat(),
            "budget": state.get("budget"),
            "travelers": state.get("travelers", 1),
            "preferences": state.get("preferences", []),
            "research": research_data,
        },
        ensure_ascii=False,
    )

    try:
        text = await chat(
            system=PLANNER_SYSTEM,
            user=user_msg,
            max_tokens=8192,
            model=s.planner_model or s.llm_model,
        )
        plan = extract_json(text)
    except Exception as e:
        logger.exception("plan_trip failed")
        return {"status": "error", "error": f"行程编排失败：{e}"}

    return {"current_plan": plan, "status": "validating"}
