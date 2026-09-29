"""行程 API 的请求/响应模型。"""

from __future__ import annotations

from datetime import date as DateType

from pydantic import BaseModel, Field


class ActivitySchema(BaseModel):
    time_start: str
    time_end: str
    place_name: str
    category: str = "attraction"
    note: str | None = None
    cost: float = 0.0


class DayPlanSchema(BaseModel):
    day: int
    date: DateType | None = None
    hotel: str | None = None
    daily_cost: float = 0.0
    activities: list[ActivitySchema] = Field(default_factory=list)


class TravelPlanSchema(BaseModel):
    """行程响应。"""

    id: int
    title: str
    destination: str
    start_date: DateType | None = None
    end_date: DateType | None = None
    days: int = 1
    budget: float | None = None
    total_cost: float = 0.0
    plan_json: dict | None = None
    created_at: str | None = None


class TravelPlanListSchema(BaseModel):
    plans: list[TravelPlanSchema]
    total: int


class ReplanRequest(BaseModel):
    """POST /api/travel/plans/{id}/replan 请求。"""

    message: str = Field(..., description="修改请求，如'第三天删掉迪士尼'")
