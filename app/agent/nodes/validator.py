"""validator 节点：检查行程合理性。"""

from __future__ import annotations

import json
import logging

from app.agent.llm import chat, extract_json
from app.agent.prompts import VALIDATOR_SYSTEM
from app.agent.state import TravelState

logger = logging.getLogger(__name__)

_MAX_ITERATIONS = 3


async def validate_plan(state: TravelState) -> dict:
    """节点：审查行程。"""
    plan = state.get("current_plan")
    if not plan:
        return {"status": "error", "error": "无行程可审查"}

    try:
        text = await chat(
            system=VALIDATOR_SYSTEM,
            user=json.dumps(plan, ensure_ascii=False),
            max_tokens=1024,
        )
        result = extract_json(text)
    except Exception as e:
        logger.exception("validate_plan failed")
        # 审查失败不阻塞，默认通过
        return {"validation_issues": [], "needs_replan": False, "status": "responding"}

    issues = result.get("issues", [])
    passed = result.get("passed", True)
    iterations = state.get("iterations", 0)
    needs_replan = not passed and iterations < _MAX_ITERATIONS

    return {
        "validation_issues": issues,
        "needs_replan": needs_replan,
        "status": "replanning" if needs_replan else "responding",
    }
