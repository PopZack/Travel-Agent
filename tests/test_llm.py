"""LLM 工具测试：JSON 提取与截断修复。"""

import pytest

from travel_agent.llm import extract_json, _repair_truncated_json


def test_extract_json_plain():
    """直接 JSON 字符串。"""
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_markdown_block():
    """markdown 代码块包裹。"""
    text = '```json\n{"a": 1, "b": 2}\n```'
    assert extract_json(text) == {"a": 1, "b": 2}


def test_extract_json_markdown_no_lang():
    """代码块无语言标记。"""
    text = '```\n{"x": "hello"}\n```'
    assert extract_json(text) == {"x": "hello"}


def test_extract_json_with_surrounding_text():
    """JSON 前后有多余文字。"""
    text = '这是结果：\n{"destination": "京都", "days": 4}\n以上。'
    assert extract_json(text) == {"destination": "京都", "days": 4}


def test_extract_json_nested():
    """嵌套 JSON。"""
    text = '前缀 {"outer": {"inner": [1, 2, 3]}} 后缀'
    assert extract_json(text) == {"outer": {"inner": [1, 2, 3]}}


def test_extract_json_truncated_object():
    """截断的对象 JSON — 缺右括号但值完整时应修复。"""
    text = '{"destination": "京都", "days": 4'
    result = extract_json(text)
    assert result["destination"] == "京都"
    assert result["days"] == 4


def test_extract_json_truncated_with_missing_value():
    """截断在值缺失处（budget: 无值）— 无法修复，抛 ValueError。"""
    text = '{"destination": "京都", "days": 4, "budget":'
    with pytest.raises(ValueError):
        extract_json(text)


def test_extract_json_truncated_array():
    """截断的数组 JSON — 应修复。"""
    text = '{"styles": ["culture", "nature", "food"'
    result = extract_json(text)
    assert result["styles"] == ["culture", "nature", "food"]


def test_extract_json_truncated_string():
    """截断在字符串中间 — 应补引号。"""
    text = '{"note": "这是一段未完的备注'
    result = extract_json(text)
    assert "note" in result


def test_extract_json_raises_on_garbage():
    """完全无法解析时抛 ValueError。"""
    with pytest.raises(ValueError):
        extract_json("这不是 JSON")


def test_repair_simple_truncation():
    """修复简单截断：缺右括号。"""
    repaired = _repair_truncated_json('{"a": 1')
    assert repaired == '{"a": 1}'


def test_repair_nested_truncation():
    """修复嵌套截断：缺多个右括号。"""
    repaired = _repair_truncated_json('{"a": {"b": [1, 2')
    # 应补 ] 和两个 }
    assert repaired.endswith("]}}")


def test_repair_string_truncation():
    """截断在字符串中间：补引号再补括号。"""
    repaired = _repair_truncated_json('{"note": "hello')
    assert repaired == '{"note": "hello"}'
