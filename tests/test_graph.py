"""LangGraph 节点流转测试。

用 monkeypatch 把 Claude 调用和工具都换成桩，测图的拓扑与 interrupt 行为。
"""

from datetime import date

import pytest

from travel_agent.models import (
    Critique,
    Itinerary,
    ParsedIntent,
    Quote,
    QuoteItem,
    ResearchResult,
    TravelStyle,
)
from travel_agent.state import TravelState


@pytest.fixture
def fake_intent():
    return ParsedIntent(
        destination="京都",
        destination_iata="KIX",
        origin="上海",
        origin_iata="PVG",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 4),
        days=4,
        adults=2,
        budget_cny=15000,
        styles=[TravelStyle.CULTURE],
    )


def test_state_is_typeddict(fake_intent):
    """状态能正确构造。"""
    s: TravelState = {
        "user_query": "去京都",
        "intent": fake_intent,
        "iterations": 0,
        "status": "parsing",
    }
    assert s["intent"].destination == "京都"
    assert s["iterations"] == 0


def test_graph_topology():
    """图能构建并包含所有节点。"""
    from travel_agent.graph import build_graph

    graph = build_graph()
    # 编译后的图有 nodes 属性
    node_names = set(graph.nodes.keys())
    expected = {"parse_intent", "research", "plan", "critique", "present", "book"}
    assert expected.issubset(node_names)


def test_critique_passed_routes_to_present(fake_intent):
    """critique 通过 → after_critique 返回 present。"""
    from travel_agent.graph import _after_critique

    state: TravelState = {
        "critique": Critique(passed=True),
        "iterations": 0,
        "status": "critiquing",
    }
    assert _after_critique(state) == "present"


def test_critique_failed_routes_to_plan(fake_intent):
    """critique 不通过且未超限 → 回 plan。"""
    from travel_agent.graph import _after_critique

    state: TravelState = {
        "critique": Critique(passed=False, issues=["赶路太多"]),
        "iterations": 1,
        "status": "planning",
    }
    assert _after_critique(state) == "plan"


def test_critique_failed_over_limit_routes_to_present():
    """critique 不通过但超重排上限 → 兜底 present。"""
    from travel_agent.graph import _after_critique

    state: TravelState = {
        "critique": Critique(passed=False, issues=["还是不行"]),
        "iterations": 3,
        "status": "planning",
    }
    assert _after_critique(state) == "present"


def test_quote_total_sums_items():
    """报价总价 = 各项之和。"""
    q = Quote(
        items=[
            QuoteItem(type="flight", description="MU123", price_cny=3000),
            QuoteItem(type="hotel", description="酒店", price_cny=4000),
            QuoteItem(type="activity", description="门票", price_cny=500),
        ],
        total_cny=7500,
    )
    assert sum(i.price_cny for i in q.items) == q.total_cny
