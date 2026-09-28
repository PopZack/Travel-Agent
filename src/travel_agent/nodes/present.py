"""present 节点：把行程转成报价单，准备展示给用户确认。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from travel_agent.models import Quote, QuoteItem
from travel_agent.state import TravelState


async def present(state: TravelState) -> dict:
    """节点：生成报价。"""
    itinerary = state.get("itinerary")
    research = state.get("research")
    if not itinerary:
        return {"status": "error", "error": "无行程可报价"}

    items: list[QuoteItem] = []

    # 机票：取最便宜的一班
    if research and research.flights:
        f = min(research.flights, key=lambda x: x.price_cny)
        items.append(
            QuoteItem(
                type="flight",
                description=f"{f.airline} {f.flight_number} {f.origin_iata}→{f.dest_iata} "
                f"{f.depart_time:%m-%d %H:%M}",
                price_cny=f.price_cny,
                refundable=False,
                cancel_policy="机票一经出票不可退（具体以航司为准）",
            )
        )

    # 酒店：取行程里出现的或最便宜的
    if research and research.hotels:
        h = min(research.hotels, key=lambda x: x.total_cny)
        items.append(
            QuoteItem(
                type="hotel",
                description=f"{h.name} {h.check_in}~{h.check_out} {h.stars or '-'}星",
                price_cny=h.total_cny,
                refundable=True,
                cancel_policy="入住前 48 小时可免费取消",
            )
        )

    # 活动：累加行程里的活动费用
    for day in itinerary.days:
        for act in day.activities:
            if act.cost_cny > 0:
                items.append(
                    QuoteItem(
                        type="activity",
                        description=f"D{day.day} {act.time_start} {act.place.name}",
                        price_cny=act.cost_cny,
                        refundable=True,
                        cancel_policy="活动开始前 24 小时可取消",
                    )
                )

    total = sum(i.price_cny for i in items)
    quote = Quote(
        items=items,
        total_cny=total,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    return {"quote": quote, "status": "awaiting_confirm"}
