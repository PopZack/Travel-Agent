"""check_information 节点：检查必填字段是否完整。"""

from __future__ import annotations

from app.agent.state import TravelState


def check_information(state: TravelState) -> dict:
    """节点：检查信息完整性，设置 missing_fields 和 needs_more_info。"""
    missing: list[str] = []

    if not state.get("destination"):
        missing.append("destination")

    # days 或 (start_date + end_date) 至少有一个
    has_days = state.get("days") is not None
    has_dates = state.get("start_date") and state.get("end_date")
    if not has_days and not has_dates:
        missing.append("days")

    needs_more = bool(missing) and state.get("intent") == "travel_plan"

    return {
        "missing_fields": missing,
        "needs_more_info": needs_more,
        "status": "asking" if needs_more else "planning",
    }
