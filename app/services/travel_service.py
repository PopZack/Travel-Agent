"""行程服务：行程的业务逻辑。"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.repositories.travel_repository import (
    delete_plan,
    get_plan,
    list_plans,
    save_plan,
    update_plan,
)


class TravelService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def save(
        self,
        conversation_id: str | None,
        title: str,
        destination: str,
        plan_data: dict,
        **kwargs,
    ) -> dict:
        """保存行程，返回 plan_id 和基本信息。"""
        plan = save_plan(
            self._db, conversation_id, title, destination, plan_data, **kwargs
        )
        return {"id": plan.id, "title": plan.title, "destination": plan.destination}

    def get(self, plan_id: int) -> dict | None:
        """获取行程详情。"""
        plan = get_plan(self._db, plan_id)
        if not plan:
            return None
        return {
            "id": plan.id,
            "title": plan.title,
            "destination": plan.destination,
            "plan": json.loads(plan.plan_json),
            "total_cost": plan.total_cost,
        }

    def list(self, conversation_id: str | None = None) -> list[dict]:
        """列出行程。"""
        plans = list_plans(self._db, conversation_id)
        return [
            {"id": p.id, "title": p.title, "destination": p.destination, "total_cost": p.total_cost}
            for p in plans
        ]

    def update(self, plan_id: int, plan_data: dict, total_cost: float = 0.0) -> dict | None:
        """更新行程。"""
        plan = update_plan(self._db, plan_id, plan_data, total_cost)
        if not plan:
            return None
        return {"id": plan.id, "title": plan.title}

    def delete(self, plan_id: int) -> bool:
        """删除行程。"""
        return delete_plan(self._db, plan_id)
