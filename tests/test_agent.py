"""Agent 节点测试。"""

import pytest


def test_check_information_complete():
    """信息完整 → needs_more_info=False。"""
    from app.agent.nodes.check_info import check_information

    state = {"destination": "东京", "days": 5, "intent": "travel_plan"}
    result = check_information(state)
    assert result["needs_more_info"] is False
    assert result["missing_fields"] == []


def test_check_information_missing_destination():
    """缺目的地 → needs_more_info=True。"""
    from app.agent.nodes.check_info import check_information

    state = {"days": 5, "intent": "travel_plan"}
    result = check_information(state)
    assert result["needs_more_info"] is True
    assert "destination" in result["missing_fields"]


def test_check_information_missing_days():
    """缺天数 → needs_more_info=True。"""
    from app.agent.nodes.check_info import check_information

    state = {"destination": "东京", "intent": "travel_plan"}
    result = check_information(state)
    assert result["needs_more_info"] is True
    assert "days" in result["missing_fields"]


def test_check_information_has_dates_no_days():
    """有 start_date + end_date 但无 days → 信息完整。"""
    from app.agent.nodes.check_info import check_information

    state = {
        "destination": "东京",
        "start_date": "2026-11-01",
        "end_date": "2026-11-05",
        "intent": "travel_plan",
    }
    result = check_information(state)
    assert result["needs_more_info"] is False


def test_check_information_not_travel_plan():
    """非 travel_plan intent → 不追问。"""
    from app.agent.nodes.check_info import check_information

    state = {"intent": "general_chat"}
    result = check_information(state)
    assert result["needs_more_info"] is False


def test_build_questions_destination():
    """缺目的地 → 生成目的地选项。"""
    from app.agent.nodes.ask_user import _build_questions

    questions = _build_questions(["destination"], {})
    assert len(questions) >= 1
    dest_q = questions[0]
    assert dest_q["field"] == "destination"
    assert len(dest_q["options"]) > 0
    assert dest_q["input_type"] == "select"


def test_build_questions_days():
    """缺天数 → 生成天数选项。"""
    from app.agent.nodes.ask_user import _build_questions

    questions = _build_questions(["days"], {})
    days_q = next(q for q in questions if q["field"] == "days")
    assert len(days_q["options"]) == 5  # 3,4,5,7,10


def test_extract_json_from_codeblock():
    """extract_json 能解析代码块包裹的 JSON。"""
    from app.agent.llm import extract_json

    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_with_text():
    """extract_json 能从前后文字中提取 JSON。"""
    from app.agent.llm import extract_json

    assert extract_json('结果：{"dest": "东京"} 完成') == {"dest": "东京"}
