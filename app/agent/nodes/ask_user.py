"""ask_user 节点：信息不完整时生成结构化追问选项。"""

from __future__ import annotations

import logging

from app.agent.llm import chat
from app.agent.prompts import ASK_USER_SYSTEM
from app.agent.state import TravelState

logger = logging.getLogger(__name__)

# 常见目的地选项
_DESTINATION_OPTIONS = [
    ("东京", "日本首都，美食与都市文化"),
    ("京都", "古都，寺庙与红叶"),
    ("大阪", "关西美食之都"),
    ("北海道", "自然与温泉"),
    ("曼谷", "泰国首都，性价比高"),
    ("清迈", "泰北小城，慢生活"),
    ("新加坡", "城市国家，干净便利"),
    ("首尔", "韩国首都，购物美食"),
    ("巴黎", "浪漫之都"),
    ("伦敦", "英伦风情"),
    ("北京", "皇城根下"),
    ("上海", "魔都风情"),
    ("成都", "熊猫与火锅"),
    ("云南", "彩云之南"),
]

# 天数选项
_DAYS_OPTIONS = [3, 4, 5, 7, 10]

# 人数选项
_TRAVELERS_OPTIONS = [1, 2, 3, 4, 5]

# 预算选项
_BUDGET_OPTIONS = [
    ("3000", "经济型"),
    ("5000", "舒适型"),
    ("10000", "品质型"),
    ("15000", "高端型"),
    ("30000", "豪华型"),
]


def _build_questions(missing: list[str], state: TravelState) -> list[dict]:
    """根据缺失字段构建结构化追问。"""
    questions = []

    if "destination" in missing:
        questions.append({
            "field": "destination",
            "question": "你想去哪里？",
            "input_type": "select",
            "options": [
                {"label": name, "value": name, "description": desc}
                for name, desc in _DESTINATION_OPTIONS
            ],
        })

    if "days" in missing:
        questions.append({
            "field": "days",
            "question": "计划玩几天？",
            "input_type": "select",
            "options": [
                {"label": f"{d} 天", "value": str(d)}
                for d in _DAYS_OPTIONS
            ],
        })

    # 预算和人数是可选的，但如果缺失也提供选项
    if not state.get("budget"):
        questions.append({
            "field": "budget",
            "question": "预算大概多少？",
            "input_type": "select",
            "options": [
                {"label": f"{val}元（{desc}）", "value": val}
                for val, desc in _BUDGET_OPTIONS
            ],
        })

    if not state.get("travelers"):
        questions.append({
            "field": "travelers",
            "question": "几个人出行？",
            "input_type": "select",
            "options": [
                {"label": f"{n} 人", "value": str(n)}
                for n in _TRAVELERS_OPTIONS
            ],
        })

    return questions


async def ask_user(state: TravelState) -> dict:
    """节点：生成结构化追问选项。"""
    missing = state.get("missing_fields", [])
    questions = _build_questions(missing, state)

    # 也生成一句友好的引导文字
    missing_zh = "、".join(_field_name(f) for f in missing)
    try:
        response = await chat(
            system=ASK_USER_SYSTEM.format(
                missing_fields=missing_zh,
                known_info=str({k: state.get(k) for k in ("destination", "days", "budget") if state.get(k)}),
            ),
            user=state.get("user_message", ""),
            max_tokens=256,
        )
    except Exception as e:
        logger.warning("ask_user LLM failed: %s", e)
        response = f"请补充以下信息：{missing_zh}"

    return {"response": response, "status": "done"}


def _field_name(field: str) -> str:
    return {"destination": "目的地", "days": "天数", "budget": "预算", "travelers": "人数"}.get(field, field)
