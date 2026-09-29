"""pydantic 数据模型 — 贯穿意图、研究结果、行程、报价、预订结果。

所有模型都是 pydantic v2，便于序列化进 LangGraph 状态与 Streamlit 展示。
"""

from __future__ import annotations

from datetime import date, datetime, time
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# ---------- 意图 ----------

class TravelStyle(str, Enum):
    CULTURE = "culture"
    NATURE = "nature"
    FOOD = "food"
    FAMILY = "family"
    BUDGET = "budget"
    LUXURY = "luxury"
    ADVENTURE = "adventure"


class ParsedIntent(BaseModel):
    """从用户自然语言抽取的结构化意图。"""

    destination: str = Field(description="目的地，如 '京都'")
    destination_iata: str | None = Field(default=None, description="目的地最近机场 IATA，如 'KIX'")
    origin: str | None = Field(default=None, description="出发地")
    origin_iata: str | None = Field(default=None, description="出发地最近机场 IATA")
    start_date: date | None = None
    end_date: date | None = None
    days: int | None = Field(default=None, ge=1, le=30)
    adults: int = Field(default=1, ge=1, le=10)
    children: int = Field(default=0, ge=0, le=10)
    budget_cny: float | None = Field(default=None, gt=0, description="总预算（人民币）")
    styles: list[TravelStyle] = Field(default_factory=list)
    notes: str | None = Field(default=None, description="其他自由文本偏好")


# ---------- 研究结果 ----------

class FlightOffer(BaseModel):
    airline: str
    flight_number: str
    depart_time: datetime
    arrive_time: datetime
    origin_iata: str
    dest_iata: str
    price_cny: float
    stops: int = 0
    deep_link: str | None = None


class HotelOffer(BaseModel):
    name: str
    stars: float | None = None
    check_in: date
    check_out: date
    price_per_night_cny: float
    total_cny: float
    location: str | None = None
    deep_link: str | None = None


class Place(BaseModel):
    name: str = "未命名"
    category: str = "attraction"  # 宽容 LLM 返回的各种类型
    rating: float | None = None
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    price_level: str | None = None  # LLM 可能返回各种格式，宽容用 str
    opening_hours: str | None = None


class WeatherDay(BaseModel):
    date: date
    temp_high_c: float
    temp_low_c: float
    condition: str  # "晴/多云/雨/..."
    precip_prob: float | None = None


class RouteSegment(BaseModel):
    from_name: str
    to_name: str
    distance_km: float
    duration_min: float
    mode: Literal["drive", "walk", "transit"] = "drive"


class ResearchResult(BaseModel):
    """research 节点聚合所有工具结果。任一子字段可缺失（工具失败时）。"""

    flights: list[FlightOffer] = Field(default_factory=list)
    hotels: list[HotelOffer] = Field(default_factory=list)
    attractions: list[Place] = Field(default_factory=list)
    restaurants: list[Place] = Field(default_factory=list)
    weather: list[WeatherDay] = Field(default_factory=list)
    exchange_rate: float | None = Field(default=None, description="CNY→目的地货币")
    visa_info: str | None = Field(default=None, description="签证要求提示")
    partial: list[str] = Field(default_factory=list, description="失败的工具名")


# ---------- 行程 ----------

class Activity(BaseModel):
    time_start: time
    time_end: time
    place: Place
    note: str | None = None
    cost_cny: float = 0.0


class DayPlan(BaseModel):
    day: int
    date: date
    activities: list[Activity] = Field(default_factory=list)
    transit: list[RouteSegment] = Field(default_factory=list)
    hotel: str | None = None
    daily_cost_cny: float = 0.0


class Itinerary(BaseModel):
    days: list[DayPlan]
    total_cost_cny: float = 0.0


# ---------- 审查 ----------

class Critique(BaseModel):
    passed: bool
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


# ---------- 报价与预订 ----------

class QuoteItem(BaseModel):
    type: Literal["flight", "hotel", "activity"]
    description: str
    price_cny: float
    refundable: bool = False
    cancel_policy: str | None = None


class Quote(BaseModel):
    items: list[QuoteItem]
    total_cny: float
    currency: str = "CNY"
    expires_at: datetime | None = None


class BookingResult(BaseModel):
    success: bool
    pnr: str | None = None
    confirmation_codes: list[str] = Field(default_factory=list)
    total_paid_cny: float | None = None
    simulated: bool = False  # test 模式为 True
    error: str | None = None
    booked_at: datetime | None = None
