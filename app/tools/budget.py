"""预算工具：计算行程费用，无需外部 API。"""

from __future__ import annotations


class BudgetTool:
    """预算计算与校验工具。"""

    async def calculate_total(self, daily_costs: list[float]) -> float:
        """累加每日费用。"""
        return round(sum(daily_costs), 2)

    async def check_budget(self, total_cost: float, budget: float | None) -> dict:
        """检查是否超预算。"""
        if budget is None:
            return {"over_budget": False, "total": total_cost, "budget": None, "surplus": None}
        return {
            "over_budget": total_cost > budget,
            "total": total_cost,
            "budget": budget,
            "surplus": round(budget - total_cost, 2),
        }

    async def split_budget(
        self, budget: float, days: int, hotel_ratio: float = 0.35, food_ratio: float = 0.25
    ) -> dict:
        """按比例分配预算到各类支出。"""
        transport_ratio = 0.15
        tickets_ratio = 0.15
        other_ratio = 1.0 - hotel_ratio - food_ratio - transport_ratio - tickets_ratio

        return {
            "hotel": round(budget * hotel_ratio, 2),
            "food": round(budget * food_ratio, 2),
            "transport": round(budget * transport_ratio, 2),
            "tickets": round(budget * tickets_ratio, 2),
            "other": round(budget * other_ratio, 2),
            "per_day": round(budget / days, 2) if days > 0 else 0,
        }
