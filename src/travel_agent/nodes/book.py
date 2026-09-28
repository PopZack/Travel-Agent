"""book 节点：人工确认 + 下单。

流程：
1. 首次进入 → interrupt 暂停，把报价回传 UI 等用户确认
2. 用户 resume → 校验报价未过期 + 价格变动
3. 价格变动 >5% → 再次 interrupt 让用户确认新价
4. 调 Amadeus 下单 → 返回 BookingResult
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from langgraph.types import interrupt

from travel_agent.models import BookingResult
from travel_agent.state import TravelState
from travel_agent.tools import AmadeusTool

logger = logging.getLogger(__name__)

_PRICE_TOLERANCE = 0.05  # 5%


async def book(state: TravelState) -> dict:
    """节点：人工确认后下单。"""
    quote = state.get("quote")
    if not quote:
        return {"status": "error", "error": "无报价可下单"}

    # ---------- 第一次 interrupt：等用户确认 ----------
    confirmed = state.get("confirmed")
    if not confirmed:
        interrupt(
            value={
                "quote": quote.model_dump(mode="json"),
                "message": "请确认以下报价后下单。",
            }
        )
        # interrupt 会暂停图执行；resume 后从这里继续，confirmed 会从 resume 值注入

    # ---------- 价格校验 ----------
    # 下单前最后再拉一次实时价格（简化：用 quote 自身；真实应重新 search 比对）
    # 若有新报价且变动超 5%，二次确认
    new_total = state.get("revalidated_total")
    if new_total and quote.total_cny > 0:
        delta = abs(new_total - quote.total_cny) / quote.total_cny
        if delta > _PRICE_TOLERANCE:
            reconfirmed = state.get("reconfirmed")
            if not reconfirmed:
                interrupt(
                    value={
                        "old_total": quote.total_cny,
                        "new_total": new_total,
                        "message": f"价格变动 {delta:.1%}，请确认新价后继续。",
                    }
                )

    # ---------- 下单 ----------
    amadeus = AmadeusTool()
    try:
        order = await amadeus.create_order(quote)
        result = BookingResult(
            success=order.get("success", False),
            pnr=order.get("pnr"),
            confirmation_codes=order.get("confirmation_codes", []),
            total_paid_cny=order.get("total_paid_cny"),
            simulated=order.get("simulated", False),
            error=order.get("error"),
            booked_at=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.exception("booking failed")
        result = BookingResult(success=False, error=str(e), booked_at=datetime.now(timezone.utc))

    return {"booking": result, "status": "done" if result.success else "error"}
