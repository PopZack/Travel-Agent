"""行程 API：CRUD /api/travel/plans。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.travel import ReplanRequest, TravelPlanListSchema, TravelPlanSchema
from app.services.travel_service import TravelService

router = APIRouter(prefix="/api/travel", tags=["travel"])


@router.get("/plans", response_model=TravelPlanListSchema)
async def list_plans(
    conversation_id: str | None = None, db: Session = Depends(get_db)
) -> TravelPlanListSchema:
    """列出行程。"""
    service = TravelService(db)
    plans = service.list(conversation_id)
    return TravelPlanListSchema(plans=plans, total=len(plans))  # type: ignore[arg-type]


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: int, db: Session = Depends(get_db)) -> dict:
    """获取行程详情。"""
    service = TravelService(db)
    plan = service.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="行程不存在")
    return plan


@router.delete("/plans/{plan_id}")
async def delete_plan(plan_id: int, db: Session = Depends(get_db)) -> dict:
    """删除行程。"""
    service = TravelService(db)
    if not service.delete(plan_id):
        raise HTTPException(status_code=404, detail="行程不存在")
    return {"deleted": True}


@router.post("/plans/{plan_id}/replan")
async def replan_plan(
    plan_id: int, req: ReplanRequest, db: Session = Depends(get_db)
) -> dict:
    """重新规划行程（占位：实际 re-planning 通过 /api/chat 的 modify_plan intent 完成）。"""
    service = TravelService(db)
    plan = service.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="行程不存在")
    # 提示用户通过 chat 接口完成修改
    return {
        "message": "请通过 POST /api/chat 发送修改请求，如 '第三天删掉迪士尼'。",
        "plan_id": plan_id,
        "current_plan": plan,
    }
