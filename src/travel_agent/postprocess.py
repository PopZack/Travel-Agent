"""后处理：报价生成、交通段填充。

从 plan/present 节点抽出共享逻辑，供 LangGraph 节点和流式编排共用，避免重复。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from travel_agent.models import Itinerary, Quote, QuoteItem, ResearchResult, RouteSegment
from travel_agent.tools import AmapTool, RoutingTool

logger = logging.getLogger(__name__)


def build_quote(itinerary: Itinerary, research: ResearchResult | None) -> Quote:
    """从行程 + 研究结果生成报价单。

    机票取最便宜一班，酒店取最便宜一家，活动按行程逐条累加。
    """
    items: list[QuoteItem] = []

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
    return Quote(
        items=items,
        total_cny=total,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )


async def fill_transit(itinerary: Itinerary) -> Itinerary:
    """为每天相邻活动填充交通段（距离/时长）。

    优先用高德路线规划，回退 OSRM，再回退直线距离估算。
    需要活动地点有坐标；无坐标则跳过。
    """
    amap = AmapTool()
    routing = RoutingTool()

    for day in itinerary.days:
        segments: list[RouteSegment] = []
        acts = day.activities
        for i in range(len(acts) - 1):
            a, b = acts[i], acts[i + 1]
            if not (a.place.lat and a.place.lng and b.place.lat and b.place.lng):
                continue
            from_coord = (a.place.lat, a.place.lng)
            to_coord = (b.place.lat, b.place.lng)
            seg = None
            try:
                seg = await amap.route(
                    a.place.name, b.place.name, from_coord, to_coord, mode="driving"
                )
            except Exception as e:
                logger.debug("amap route failed: %s", e)
            if not seg:
                try:
                    seg = await routing.route(
                        a.place.name, b.place.name, from_coord, to_coord, mode="drive"
                    )
                except Exception as e:
                    logger.debug("osrm route failed: %s", e)
            if seg:
                segments.append(seg)
        day.transit = segments

    return itinerary
