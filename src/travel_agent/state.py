"""LangGraph 状态定义。

用 TypedDict 而非 pydantic，因为 LangGraph 内部对 TypedDict 支持最好；
pydantic 模型作为字段值嵌套其中。
"""

from __future__ import annotations

from typing import TypedDict

from travel_agent.models import (
    BookingResult,
    Critique,
    Itinerary,
    ParsedIntent,
    Quote,
    ResearchResult,
)


class TravelState(TypedDict, total=False):
    # 输入
    messages: list[dict]          # 对话历史 [{"role":..., "content":...}]
    user_query: str

    # 流程中间态
    intent: ParsedIntent | None
    research: ResearchResult | None
    itinerary: Itinerary | None
    critique: Critique | None
    quote: Quote | None

    # 结果
    booking: BookingResult | None

    # 控制
    status: str        # parsing/researching/planning/critiquing/presenting/awaiting_confirm/booking/done/error
    iterations: int    # plan-critique 回环次数
    error: str | None
    thread_id: str     # LangGraph 线程 id（检查点用）
