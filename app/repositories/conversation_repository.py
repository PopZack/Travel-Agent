"""对话仓储：消息历史的 CRUD。"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.conversation import Conversation, Message


def create_conversation(db: Session, title: str | None = None) -> Conversation:
    """新建会话，返回带 conversation_id 的对象。"""
    conv = Conversation(conversation_id=str(uuid.uuid4()), title=title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def get_or_create_conversation(db: Session, conversation_id: str | None) -> Conversation:
    """按 ID 获取会话，不存在则新建。"""
    if conversation_id:
        conv = db.query(Conversation).filter_by(conversation_id=conversation_id).first()
        if conv:
            return conv
    return create_conversation(db)


def save_message(db: Session, conversation_id: str, role: str, content: str) -> Message:
    """保存一条消息。"""
    msg = Message(conversation_id=conversation_id, role=role, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def get_messages(db: Session, conversation_id: str, limit: int = 50) -> list[Message]:
    """获取会话的消息历史。"""
    return (
        db.query(Message)
        .filter_by(conversation_id=conversation_id)
        .order_by(Message.id.desc())
        .limit(limit)
        .all()[::-1]
    )
