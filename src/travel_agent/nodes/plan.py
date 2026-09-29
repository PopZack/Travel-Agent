"""plan 节点：用 LLM 把研究结果编排成按天行程。

约束：
- 景点开放时间与到达时间兼容
- 单日景点数受偏好调节（少走路 → 少景点）
- 相邻活动间插入交通时长
- 预算校验

当外部研究数据为空（未配置 API key）时，LLM 用自身知识排行程。
"""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta

from travel_agent.config import get_settings
from travel_agent.llm import chat, extract_json
from travel_agent.models import Itinerary, Place
from travel_agent.state import TravelState

logger = logging.getLogger(__name__)

_SYSTEM = """你是旅行规划师。编排按天行程。

每天必须包含：景点、午餐、晚餐、住宿费。cost_cny 是人民币。
- 景点门票：如实估算（如清水寺400日元≈20元）
- 午餐/晚餐：每人每餐 100-300 元
- 住宿：每晚 500-1500 元，写在当天 daily_cost_cny 里
- daily_cost_cny = 当天所有活动 cost_cny 之和 + 住宿费
- total_cost_cny = 所有天之和，不超预算

先输出紧凑JSON（一行），然后输出一行 ===TEXT===，最后输出行程概览（中文，每天几行，简洁）。

格式：
{"days":[{"day":1,"date":"YYYY-MM-DD","activities":[{"time_start":"09:00","time_end":"11:30","place":{"name":"清水寺","category":"attraction"},"note":"提示","cost_cny":20}],"hotel":"酒店名","daily_cost_cny":1200}],"total_cost_cny":4800}
===TEXT===
第1天 11-01
上午 清水寺（门票20元）
中午 京都拉面（600元）"""


async def plan(state: TravelState) -> dict:
    """节点：编排行程。"""
    intent = state.get("intent")
    if not intent:
        return {"status": "error", "error": "缺少意图"}

    research = state.get("research")
    s = get_settings()

    # 推算日期
    start = intent.start_date or date.today() + timedelta(days=30)
    days = intent.days or (
        (intent.end_date - intent.start_date).days if intent.start_date and intent.end_date else 4
    )

    research_data = research.model_dump(mode="json") if research else None

    user_msg = json.dumps(
        {
            "intent": intent.model_dump(mode="json"),
            "research": research_data,
            "start_date": start.isoformat(),
            "days": days,
            "note": "research 为 null 表示没有外部 API 数据，请用你自己的知识推荐景点和餐厅。"
            if not research_data
            else None,
        },
        ensure_ascii=False,
    )

    try:
        text = chat(
            system=_SYSTEM,
            user=user_msg,
            max_tokens=8192,
            model=s.planner_model or s.llm_model,
        )
        data = extract_json(text)
        # 规范化每个 activity 的 place
        for d in data.get("days", []):
            for a in d.get("activities", []):
                p = a.get("place", {})
                if isinstance(p, dict):
                    # 补默认 category
                    p.setdefault("category", "attraction")
                    a["place"] = Place(**p).model_dump()
        itinerary = Itinerary(**data)
    except Exception as e:
        logger.exception("plan failed")
        return {"status": "error", "error": f"行程编排失败：{e}"}

    return {"itinerary": itinerary, "status": "critiquing"}
