"""构建并编译 LangGraph 状态图。

流转：
  START → parse_intent → research → plan → critique
  critique.passed → present → await_confirm(book) → END
  critique.not_passed & iterations<3 → plan（回环）
  critique.not_passed & iterations>=3 → present（兜底）
  任何 error → END
"""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from travel_agent.nodes import book, critique, parse_intent, plan, present, research
from travel_agent.state import TravelState

_MAX_ITERATIONS = 3


def _after_critique(state: TravelState) -> str:
    """条件边：审查通过 → present；不通过且未超限 → plan；否则兜底 present。"""
    if state.get("status") == "error":
        return END
    c = state.get("critique")
    if c and c.passed:
        return "present"
    if state.get("iterations", 0) >= _MAX_ITERATIONS:
        return "present"  # 超过重排上限，直接展示当前行程
    return "plan"


def _after_present(state: TravelState) -> str:
    """present 之后进 book（book 内部用 interrupt 等确认）。"""
    if state.get("status") == "error":
        return END
    return "book"


def _increment_iteration(state: TravelState) -> dict:
    """进 plan 前累加迭代计数（用于回环控制）。"""
    return {"iterations": state.get("iterations", 0) + 1}


def build_graph():
    """构建并编译旅行 Agent 状态图。"""
    g = StateGraph(TravelState)

    g.add_node("parse_intent", parse_intent)
    g.add_node("research", research)
    g.add_node("plan", plan)
    g.add_node("critique", critique)
    g.add_node("present", present)
    g.add_node("book", book)

    g.add_edge(START, "parse_intent")
    g.add_edge("parse_intent", "research")
    g.add_edge("research", "plan")
    g.add_edge("plan", "critique")
    g.add_conditional_edges("critique", _after_critique, ["plan", "present", END])
    g.add_conditional_edges("present", _after_present, ["book", END])
    g.add_edge("book", END)

    return g.compile(checkpointer=MemorySaver())
