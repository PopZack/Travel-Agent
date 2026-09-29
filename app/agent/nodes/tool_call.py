"""tool_call 节点：并行调度工具，查景点/餐厅/天气/汇率/签证。"""

from __future__ import annotations

import asyncio
import logging

from app.agent.state import TravelState
from app.tools import AmapTool, ExchangeTool, PlacesTool, VisaTool, WeatherTool

logger = logging.getLogger(__name__)


async def call_tools(state: TravelState) -> dict:
    """节点：并行调工具，收集景点/餐厅/天气/汇率/签证。"""
    destination = state.get("destination")
    if not destination:
        return {"tool_results": [], "status": "planning"}

    amap = AmapTool()
    places = PlacesTool()
    weather_tool = WeatherTool()
    exchange = ExchangeTool()
    visa = VisaTool()

    partial: list[str] = []

    async def _search_attractions():
        r = await amap.search_places(destination, category="attraction")
        if r:
            return r
        return await places.search_attractions(destination)

    async def _search_restaurants():
        r = await amap.search_places(destination, category="restaurant")
        if r:
            return r
        return await places.search_restaurants(destination)

    tasks = [
        asyncio.create_task(_search_attractions(), name="attractions"),
        asyncio.create_task(_search_restaurants(), name="restaurants"),
        asyncio.create_task(exchange.cny_to(destination), name="exchange"),
        asyncio.create_task(visa.lookup(destination), name="visa"),
    ]

    # 天气：高德优先，回退 OpenWeather
    weather = []
    try:
        weather = await amap.weather(destination)
    except Exception as e:
        logger.warning("amap weather failed: %s", e)
    if not weather:
        partial.append("weather")

    named = [t.get_name() for t in tasks]
    gathered = await asyncio.gather(*tasks, return_exceptions=True)

    results: dict = {"weather": [w.model_dump(mode="json") for w in weather]}
    for name, res in zip(named, gathered):
        if isinstance(res, Exception):
            logger.warning("%s failed: %s", name, res)
            partial.append(name)
            continue
        if name == "attractions":
            results["attractions"] = [p.model_dump(mode="json") for p in res]
        elif name == "restaurants":
            results["restaurants"] = [p.model_dump(mode="json") for p in res]
        elif name == "exchange":
            results["exchange_rate"] = res
        elif name == "visa":
            results["visa_info"] = res

    results["partial"] = partial
    return {"tool_results": [results], "status": "planning"}
