"""Travel Agent — FastAPI 入口。

启动：
    uvicorn app.main:app --reload

API 文档：
    http://localhost:8000/docs
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

from app.api.routers import chat, travel
from app.common.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Travel Agent",
    description="旅行智能体 — 自然语言 → 行程规划 → 修改 → 保存",
    version="1.0.0",
)

app.include_router(chat.router)
app.include_router(travel.router)


@app.get("/")
async def root() -> dict:
    return {"name": "Travel Agent", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
