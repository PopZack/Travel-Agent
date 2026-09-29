"""SQLAlchemy 数据库引擎与会话工厂。

第一版用 SQLite，后续切 MySQL 只需改 database_url。
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.common.config import get_settings

_engine = create_engine(
    get_settings().database_url,
    echo=False,
    connect_args={"check_same_thread": False}  # SQLite 需要
    if get_settings().database_url.startswith("sqlite")
    else {},
)

_SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：获取数据库会话，请求结束自动关闭。"""
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """创建所有表。启动时调用。"""
    from app.models.conversation import Conversation, Message  # noqa: F401
    from app.models.travel import Activity, TravelPlan, TravelPlanDay  # noqa: F401

    from sqlalchemy.orm import DeclarativeBase

    # 所有模型继承自 Base，导入即注册
    Conversation.metadata.create_all(_engine)
