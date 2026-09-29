"""对话服务：管理会话和消息历史。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.conversation_repository import (
    get_messages,
    get_or_create_conversation,
    save_message,
)


class ConversationService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_or_create(self, conversation_id: str | None) -> str:
        """获取或创建会话，返回 conversation_id。"""
        conv = get_or_create_conversation(self._db, conversation_id)
        return conv.conversation_id

    def save_message(self, conversation_id: str, role: str, content: str) -> None:
        """保存消息。"""
        save_message(self._db, conversation_id, role, content)

    def get_history(self, conversation_id: str, limit: int = 50) -> list[dict]:
        """获取消息历史，返回 [{"role":..., "content":...}]。"""
        msgs = get_messages(self._db, conversation_id, limit)
        return [{"role": m.role, "content": m.content} for m in msgs]
