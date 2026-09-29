"""流式编排：把各节点的 LLM 调用拆成"流式生成 + 解析"两步。

UI 层调 run_streaming(query, on_llm_chunk)：
- on_llm_chunk 是回调，每收到一个文本片段就调一次（用于 st.write_stream 式实时渲染）
- 返回最终状态 dict

不经过 LangGraph，直接手动编排节点，以便在 LLM 生成时实时吐字。
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import date, timedelta

from travel_agent.config import get_settings
from travel_agent.llm import chat_stream, extract_json
from travel_agent.models import (
    Itinerary,
    ParsedIntent,
    Place,
    ResearchResult,
    TravelStyle,
)
from travel_agent.nodes.research import research
from travel_agent.postprocess import build_quote, fill_transit
from travel_agent.state import TravelState

logger = logging.getLogger(__name__)

# 节点 prompt 复用 nodes 里的
from travel_agent.nodes.parse_intent import _SYSTEM as _PARSE_SYSTEM
from travel_agent.nodes.plan import _SYSTEM as _PLAN_SYSTEM
from travel_agent.nodes.critique import _SYSTEM as _CRITIQUE_SYSTEM


def _stream_llm(
    system: str,
    user: str,
    *,
    max_tokens: int,
    model: str,
    on_chunk: Callable[[str], None],
    show_after: str | None = None,
) -> str:
    """流式调 LLM，逐 chunk 回调，返回完整文本。

    若指定 show_after，则遇到该分隔符后才开始回调给 UI（用于"先JSON再可读文字"的场景）。
    """
    buf = []
    showing = show_after is None  # 无分隔符则全程显示
    for chunk in chat_stream(system, user, max_tokens=max_tokens, model=model):
        buf.append(chunk)
        if showing:
            on_chunk(chunk)
        # 检查是否进入显示区
        if show_after and show_after in "".join(buf):
            showing = True
    return "".join(buf)


def run_streaming(
    query: str,
    on_chunk: Callable[[str], None],
    on_status: Callable[[str], None],
) -> dict:
    """流式运行整个流程，返回最终状态。

    Args:
        query: 用户输入
        on_chunk: LLM 文本片段回调（实时渲染用）
        on_status: 节点状态变化回调（显示"正在解析…""正在编排…"等）
    """
    s = get_settings()
    today = date.today().isoformat()
    state: TravelState = {"user_query": query, "iterations": 0, "messages": []}

    # ---------- 1. 解析意图 ----------
    on_status("🔍 解析旅行意图…")
    try:
        text = _stream_llm(
            _PARSE_SYSTEM.format(today=today),
            query,
            max_tokens=1024,
            model=s.llm_model,
            on_chunk=on_chunk,
        )
        data = extract_json(text)
        raw_styles = data.get("styles", [])
        data["styles"] = [
            TravelStyle(x) for x in raw_styles if x in {e.value for e in TravelStyle}
        ]
        intent = ParsedIntent(**data)
        state["intent"] = intent
    except Exception as e:
        logger.exception("parse_intent failed")
        return {**state, "status": "error", "error": f"意图解析失败：{e}"}

    # ---------- 2. 研究（工具层，无 LLM，不流式）----------
    on_status("🌐 搜索景点/天气/汇率…")
    try:
        import asyncio

        research_result = asyncio.run(research(state))
        state.update(research_result)
    except Exception as e:
        logger.warning("research failed: %s", e)
        state["research"] = ResearchResult(partial=[f"research: {e}"])

    # ---------- 3. 编排行程（LLM 流式，单次，不做审查以节省时间）----------
    on_status("📅 编排行程…")
    intent = state["intent"]
    r = state.get("research")

    start = intent.start_date or date.today() + timedelta(days=30)
    days = intent.days or (
        (intent.end_date - intent.start_date).days
        if intent.start_date and intent.end_date
        else 4
    )
    research_data = r.model_dump(mode="json") if r else None
    weather_data = [w.model_dump(mode="json") for w in r.weather] if r and r.weather else None
    visa_data = r.visa_info if r else None
    user_msg = json.dumps(
        {
            "intent": intent.model_dump(mode="json"),
            "research": research_data,
            "weather": weather_data,
            "visa_info": visa_data,
            "start_date": start.isoformat(),
            "days": days,
            "note": "research 为 null，请用你自己的知识推荐景点和餐厅。"
            if not research_data
            else None,
        },
        ensure_ascii=False,
    )

    try:
        text = _stream_llm(
            _PLAN_SYSTEM,
            user_msg,
            max_tokens=8192,
            model=s.planner_model or s.llm_model,
            on_chunk=on_chunk,
            show_after="===TEXT===",
        )
        # JSON 在 ===TEXT=== 之前
        json_part = text.split("===TEXT===", 1)[0] if "===TEXT===" in text else text
        data = extract_json(json_part)
        for d in data.get("days", []):
            for a in d.get("activities", []):
                p = a.get("place", {})
                if isinstance(p, dict):
                    p.setdefault("name", "未命名")
                    p.setdefault("category", "attraction")
                    a["place"] = Place(**p).model_dump()
        itinerary = Itinerary(**data)
        state["itinerary"] = itinerary
    except Exception as e:
        logger.exception("plan failed")
        return {**state, "status": "error", "error": f"行程编排失败：{e}"}

    # 填充交通段
    try:
        import asyncio

        itinerary = asyncio.run(fill_transit(itinerary))
        state["itinerary"] = itinerary
    except Exception as e:
        logger.warning("fill_transit failed: %s", e)

    # ---------- 4. 生成报价 ----------
    on_status("💰 生成报价…")
    itinerary = state["itinerary"]
    r = state.get("research")

    state["quote"] = build_quote(itinerary, r)
    state["status"] = "awaiting_confirm"
    on_status("✅ 规划完成，请确认报价")
    return state
