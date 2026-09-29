"""聊天 API：POST /api/chat。

核心接口，所有旅行规划/修改/查询通过此接口完成。
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agent.graph import build_graph
from app.agent.state import TravelState
from app.common.logging import setup_logging
from app.infrastructure.database import get_db, init_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.conversation_service import ConversationService
from app.services.travel_service import TravelService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])

setup_logging()
init_db()

_graph = build_graph()


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """处理用户消息，返回 Agent 回复。"""
    conv_service = ConversationService(db)
    travel_service = TravelService(db)

    # 获取或创建会话
    conversation_id = conv_service.get_or_create(req.conversation_id)

    # 保存用户消息
    conv_service.save_message(conversation_id, "user", req.message)

    # 获取历史
    history = conv_service.get_history(conversation_id)

    # 运行 LangGraph
    initial_state: TravelState = {
        "user_message": req.message,
        "conversation_id": conversation_id,
        "messages": history,
        "iterations": 0,
    }

    try:
        result = await _graph.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": conversation_id}},
        )
    except Exception as e:
        logger.exception("graph execution failed")
        return ChatResponse(
            conversation_id=conversation_id,
            response=f"处理失败：{e}",
            status="error",
        )

    response_text = result.get("response", "")
    status = result.get("status", "done")
    plan = result.get("current_plan")
    needs_more = result.get("needs_more_info", False)
    missing = result.get("missing_fields", [])

    # 构建结构化追问选项
    questions = []
    if needs_more:
        from app.agent.nodes.ask_user import _build_questions
        questions = _build_questions(missing, result)

    # 保存助手回复
    conv_service.save_message(conversation_id, "assistant", response_text)

    # 保存行程到数据库
    if plan and status == "done":
        try:
            travel_service.save(
                conversation_id=conversation_id,
                title=plan.get("title", "未命名行程"),
                destination=result.get("destination", ""),
                plan_data=plan,
                total_cost=plan.get("total_cost", 0.0),
            )
        except Exception as e:
            logger.warning("save plan failed: %s", e)

    return ChatResponse(
        conversation_id=conversation_id,
        response=response_text,
        status=status,
        plan=plan,
        needs_more_info=needs_more,
        missing_fields=missing,
        questions=questions,
    )
