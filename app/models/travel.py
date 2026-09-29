"""行程 ORM 模型：行程 + 按天 + 活动。"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.conversation import Base


class TravelPlan(Base):
    __tablename__ = "travel_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    destination: Mapped[str] = mapped_column(String(100))
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    days: Mapped[int] = mapped_column(Integer, default=1)
    budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    plan_json: Mapped[str] = mapped_column(Text)  # 完整行程 JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    days_rel: Mapped[list["TravelPlanDay"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )


class TravelPlanDay(Base):
    __tablename__ = "travel_plan_days"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("travel_plans.id"), index=True)
    day: Mapped[int] = mapped_column(Integer)
    date: Mapped[date | None] = mapped_column(Date, nullable=True)
    hotel: Mapped[str | None] = mapped_column(String(200), nullable=True)
    daily_cost: Mapped[float] = mapped_column(Float, default=0.0)

    plan: Mapped[TravelPlan] = relationship(back_populates="days_rel")
    activities: Mapped[list["Activity"]] = relationship(
        back_populates="day_rel", cascade="all, delete-orphan"
    )


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    day_id: Mapped[int] = mapped_column(Integer, ForeignKey("travel_plan_days.id"), index=True)
    time_start: Mapped[str] = mapped_column(String(10))
    time_end: Mapped[str] = mapped_column(String(10))
    place_name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50), default="attraction")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost: Mapped[float] = mapped_column(Float, default=0.0)

    day_rel: Mapped[TravelPlanDay] = relationship(back_populates="activities")
