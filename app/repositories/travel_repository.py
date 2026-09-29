"""行程仓储：行程的 CRUD。"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.travel import TravelPlan


def save_plan(
    db: Session,
    conversation_id: str | None,
    title: str,
    destination: str,
    plan_data: dict,
    start_date=None,
    end_date=None,
    days: int = 1,
    budget: float | None = None,
    total_cost: float = 0.0,
) -> TravelPlan:
    """保存行程。"""
    plan = TravelPlan(
        conversation_id=conversation_id,
        title=title,
        destination=destination,
        start_date=start_date,
        end_date=end_date,
        days=days,
        budget=budget,
        total_cost=total_cost,
        plan_json=json.dumps(plan_data, ensure_ascii=False),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def get_plan(db: Session, plan_id: int) -> TravelPlan | None:
    """按 ID 获取行程。"""
    return db.query(TravelPlan).get(plan_id)


def list_plans(db: Session, conversation_id: str | None = None, limit: int = 20) -> list[TravelPlan]:
    """列出行程。"""
    q = db.query(TravelPlan)
    if conversation_id:
        q = q.filter_by(conversation_id=conversation_id)
    return q.order_by(TravelPlan.id.desc()).limit(limit).all()


def update_plan(db: Session, plan_id: int, plan_data: dict, total_cost: float = 0.0) -> TravelPlan | None:
    """更新行程。"""
    plan = get_plan(db, plan_id)
    if not plan:
        return None
    plan.plan_json = json.dumps(plan_data, ensure_ascii=False)
    plan.total_cost = total_cost
    db.commit()
    db.refresh(plan)
    return plan


def delete_plan(db: Session, plan_id: int) -> bool:
    """删除行程。"""
    plan = get_plan(db, plan_id)
    if not plan:
        return False
    db.delete(plan)
    db.commit()
    return True
