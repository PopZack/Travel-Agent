"""research 节点：并行调度所有工具，聚合研究结果。

任一工具失败不中断整体流程，只记入 ResearchResult.partial。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

from travel_agent.models import ResearchResult
from travel_agent.state import TravelState
from travel_agent.tools import AmadeusTool, AmapTool, ExchangeTool, PlacesTool, WeatherTool

logger = logging.getLogger(__name__)


async def research(state: TravelState) -> dict:
    """节点：并行查机酒/景点/餐厅/天气/汇率。"""
    intent = state.get("intent")
    if not intent:
        return {"status": "error", "error": "无意图，无法研究"}

    partial: list[str] = []
    flights, hotels, attractions, restaurants, weather, rate = [], [], [], [], [], None

    amadeus = AmadeusTool()
    places = PlacesTool()
    weather_tool = WeatherTool()
    exchange = ExchangeTool()
    amap = AmapTool()

    # ---------- 并行调度 ----------
    tasks: list[asyncio.Task] = []

    # 机票（需 IATA）
    if intent.origin_iata and intent.destination_iata and intent.start_date:
        tasks.append(
            asyncio.create_task(
                amadeus.search_flights(
                    intent.origin_iata,
                    intent.destination_iata,
                    intent.start_date,
                    intent.adults,
                ),
                name="flights",
            )
        )
    else:
        partial.append("flights(缺 IATA 或日期)")

    # 酒店
    if intent.destination and intent.start_date and intent.end_date:
        tasks.append(
            asyncio.create_task(
                amadeus.search_hotels(
                    intent.destination,
                    intent.start_date,
                    intent.end_date,
                    intent.adults,
                ),
                name="hotels",
            )
        )
    else:
        partial.append("hotels(缺日期)")

    # 景点 + 餐厅（优先高德，回退 Google Places）
    async def _search_attractions():
        r = await amap.search_places(intent.destination, category="attraction")
        if r:
            return r
        return await places.search_attractions(intent.destination)

    async def _search_restaurants():
        r = await amap.search_places(intent.destination, category="restaurant")
        if r:
            return r
        return await places.search_restaurants(intent.destination)

    tasks.append(asyncio.create_task(_search_attractions(), name="attractions"))
    tasks.append(asyncio.create_task(_search_restaurants(), name="restaurants"))

    # 天气（需坐标；用第一个景点的坐标，或目的地 geocode）
    # MVP：用景点坐标；若没有则跳过
    # 这里先跑景点，再据其坐标查天气——所以天气不放进首批 gather
    # 汇率
    tasks.append(
        asyncio.create_task(exchange.cny_to(intent.destination), name="exchange")
    )

    # 收集结果（gather 保留任务名顺序）
    named = [t.get_name() for t in tasks]
    gathered = await asyncio.gather(*tasks, return_exceptions=True)
    for name, res in zip(named, gathered):
        if isinstance(res, Exception):
            logger.warning("%s failed: %s", name, res)
            partial.append(name)
            continue
        if name == "flights":
            flights = res  # type: ignore[assignment]
        elif name == "hotels":
            hotels = res  # type: ignore[assignment]
        elif name == "attractions":
            attractions = res  # type: ignore[assignment]
        elif name == "restaurants":
            restaurants = res  # type: ignore[assignment]
        elif name == "exchange":
            rate = res  # type: ignore[assignment]

    # 天气：优先高德（按城市名），回退 OpenWeather（按坐标）
    weather_days = intent.days or 7
    try:
        weather = await amap.weather(intent.destination)
    except Exception as e:
        logger.warning("amap weather failed: %s", e)
        weather = []
    if not weather and attractions and attractions[0].lat and attractions[0].lng:
        try:
            weather = await weather_tool.forecast(attractions[0].lat, attractions[0].lng, weather_days)
        except Exception as e:
            logger.warning("weather failed: %s", e)
            partial.append("weather")
    elif not weather:
        partial.append("weather(无数据)")

    result = ResearchResult(
        flights=flights,
        hotels=hotels,
        attractions=attractions,
        restaurants=restaurants,
        weather=weather,
        exchange_rate=rate,
        partial=partial,
    )
    return {"research": result, "status": "planning"}
