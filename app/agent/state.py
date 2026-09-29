"""LangGraph 状态定义。

围绕 TravelState 运行整个 Graph：
用户输入 → State → LLM 修改 State → Tool 修改 State → Planner → Validator → Response
"""

from __future__ import annotations

from typing import TypedDict


class TravelState(TypedDict, total=False):
    # 输入
    user_message: str
    conversation_id: str
    messages: list[dict]            # 对话历史 [{"role":..., "content":...}]

    # Intent + Slot
    intent: str | None              # travel_plan / modify_plan / query_weather / general_chat
    destination: str | None
    start_date: str | None
    end_date: str | None
    days: int | None
    travelers: int | None
    budget: float | None
    preferences: list[str]

    # 流程控制
    missing_fields: list[str]       # 缺失的字段名
    needs_more_info: bool           # 是否需要追问

    # 行程
    current_plan: dict | None       # 当前行程（结构化 JSON）
    plan_id: int | None             # 数据库中的行程 ID
    tool_results: list[dict]        # 工具调用结果

    # 验证
    validation_issues: list[str]
    needs_replan: bool
    iterations: int                 # replan 循环次数

    # 输出
    response: str                   # 给用户的回复
    status: str                     # understanding/checking/planning/validating/done/error
    error: str | None
