"""构建并编译 LangGraph Agent 状态图。

流程：
  START → understand_request → check_information
                                        ↓
                                  信息完整？
                                  /       \
                                No         Yes
                                ↓           ↓
                           ask_user     [intent 路由]
                                ↓           ↓
                              END    travel_plan → call_tools → plan_trip
                                     modify_plan → replan
                                     other → final_response
                                              ↓
                                     validate_plan
                                              ↓
                                        合格？
                                      /       \
                                    No         Yes
                                    ↓           ↓
                                  replan   final_response → END
                                    ↓
                              (回 validate_plan)
"""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agent.nodes.ask_user import ask_user
from app.agent.nodes.check_info import check_information
from app.agent.nodes.planner import plan_trip
from app.agent.nodes.replanner import replan
from app.agent.nodes.response import final_response
from app.agent.nodes.tool_call import call_tools
from app.agent.nodes.understand import understand_request
from app.agent.nodes.validator import validate_plan
from app.agent.state import TravelState


def _after_check(state: TravelState) -> str:
    """条件边：信息不完整 → ask_user；完整 → 按 intent 路由。"""
    if state.get("status") == "error":
        return END
    if state.get("needs_more_info"):
        return "ask_user"
    return "call_tools"


def _after_tools(state: TravelState) -> str:
    """条件边：按 intent 路由。"""
    if state.get("status") == "error":
        return END
    intent = state.get("intent", "general_chat")
    if intent == "modify_plan":
        return "replan"
    if intent == "travel_plan":
        return "plan_trip"
    return "final_response"


def _after_validate(state: TravelState) -> str:
    """条件边：不合格 → replan；合格 → final_response。"""
    if state.get("status") == "error":
        return END
    if state.get("needs_replan"):
        return "replan"
    return "final_response"


def build_graph():
    """构建并编译 Travel Agent 状态图。"""
    g = StateGraph(TravelState)

    g.add_node("understand_request", understand_request)
    g.add_node("check_information", check_information)
    g.add_node("ask_user", ask_user)
    g.add_node("call_tools", call_tools)
    g.add_node("plan_trip", plan_trip)
    g.add_node("validate_plan", validate_plan)
    g.add_node("replan", replan)
    g.add_node("final_response", final_response)

    # 主流程
    g.add_edge(START, "understand_request")
    g.add_edge("understand_request", "check_information")
    g.add_conditional_edges("check_information", _after_check, ["ask_user", "call_tools", END])
    g.add_edge("ask_user", END)

    # 工具后按 intent 路由
    g.add_conditional_edges("call_tools", _after_tools, ["plan_trip", "replan", "final_response", END])

    # 规划路径
    g.add_edge("plan_trip", "validate_plan")
    g.add_conditional_edges("validate_plan", _after_validate, ["replan", "final_response", END])

    # 修改路径：replan → validate_plan（回环检查）
    g.add_edge("replan", "validate_plan")

    # 最终回复
    g.add_edge("final_response", END)

    return g.compile(checkpointer=MemorySaver())
