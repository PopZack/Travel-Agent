"""高德地图工具：景点搜索、路线规划、天气查询。

高德 Web 服务 API 文档：https://lbs.amap.com/api/webservice/guide/api/home
免费额度：个人开发者每天 5000 次。

国内数据覆盖好；日本/海外数据有限，搜不到时返回空，由 LLM 兜底。
"""

from __future__ import annotations

import logging

import httpx

from app.tools.cache import cached
from app.common.config import get_settings
from app.tools.models import Place, RouteSegment, WeatherDay

logger = logging.getLogger(__name__)


class AmapTool:
    """高德地图工具。

    需要配置 AMAP_API_KEY。未配置时所有方法返回空，不影响流程。
    """

    BASE = "https://restapi.amap.com/v3"

    def __init__(self) -> None:
        self._key = get_settings().amap_api_key

    # ---------- 景点搜索 ----------

    @cached(ttl_seconds=3600)
    async def search_places(
        self, keyword: str, city: str = "", category: str = "attraction", limit: int = 15
    ) -> list[Place]:
        """按关键词搜景点/餐厅。

        高德 POI 搜索：/place/text
        """
        if not self._key:
            return []

        # 高德 POI 类型码：060000=风景名胜，050000=餐饮
        type_code = "060000" if category == "attraction" else "050000" if category == "restaurant" else ""
        params = {
            "key": self._key,
            "keywords": keyword,
            "city": city,
            "types": type_code,
            "offset": limit,
            "page": 1,
            "output": "json",
        }
        async with httpx.AsyncClient(timeout=10) as c:
            try:
                r = await c.get(f"{self.BASE}/place/text", params=params)
                r.raise_for_status()
            except httpx.HTTPError as e:
                logger.warning("高德景点搜索失败: %s", e)
                return []

        data = r.json()
        if data.get("status") != "1":
            logger.warning("高德搜索返回错误: %s", data.get("info"))
            return []

        results = []
        for poi in data.get("pois", [])[:limit]:
            loc = poi.get("location", "").split(",")
            results.append(
                Place(
                    name=poi.get("name", ""),
                    category=category,
                    address=poi.get("address") or poi.get("pname", "") + poi.get("cityname", ""),
                    lat=float(loc[1]) if len(loc) == 2 else None,
                    lng=float(loc[0]) if len(loc) == 2 else None,
                )
            )
        return results

    # ---------- 路线规划 ----------

    @cached(ttl_seconds=86400)
    async def route(
        self,
        from_name: str,
        to_name: str,
        from_coord: tuple[float, float],
        to_coord: tuple[float, float],
        mode: str = "driving",
    ) -> RouteSegment | None:
        """查驾车路线。高德 /direction/driving。

        坐标格式：经度,纬度（高德用 lng,lat）。
        """
        if not self._key:
            return None

        origin = f"{from_coord[1]},{from_coord[0]}"  # lng,lat
        dest = f"{to_coord[1]},{to_coord[0]}"

        if mode == "driving":
            url = f"{self.BASE}/direction/driving"
            params = {"key": self._key, "origin": origin, "destination": dest, "strategy": 0}
        else:
            # 步行用直线距离估算
            return self._estimate(from_name, to_name, from_coord, to_coord, mode)

        async with httpx.AsyncClient(timeout=10) as c:
            try:
                r = await c.get(url, params=params)
                r.raise_for_status()
            except httpx.HTTPError as e:
                logger.warning("高德路线规划失败: %s", e)
                return None

        data = r.json()
        if data.get("status") != "1":
            return None

        paths = data.get("route", {}).get("paths", [])
        if not paths:
            return None
        path = paths[0]
        return RouteSegment(
            from_name=from_name,
            to_name=to_name,
            distance_km=round(float(path["distance"]) / 1000, 1),
            duration_min=round(float(path["duration"]) / 60, 1),
            mode="drive",  # type: ignore[arg-type]
        )

    def _estimate(
        self, from_name: str, to_name: str, a: tuple[float, float], b: tuple[float, float], mode: str
    ) -> RouteSegment:
        from math import asin, cos, radians, sin, sqrt

        lat1, lon1 = a
        lat2, lon2 = b
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        h = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        km = 6371 * 2 * asin(sqrt(h))
        speed = {"walk": 4.5, "transit": 25}.get(mode, 30)
        return RouteSegment(
            from_name=from_name,
            to_name=to_name,
            distance_km=round(km, 1),
            duration_min=round(km / speed * 60, 1),
            mode=mode,  # type: ignore[arg-type]
        )

    # ---------- 天气 ----------

    @cached(ttl_seconds=1800)
    async def weather(self, city: str) -> list[WeatherDay]:
        """查天气预报。高德 /weather/weatherInfo。

        city 可以是城市名或 adcode。
        """
        if not self._key:
            return []

        from datetime import date as _date

        params = {"key": self._key, "city": city, "extensions": "all", "output": "json"}
        async with httpx.AsyncClient(timeout=10) as c:
            try:
                r = await c.get(f"{self.BASE}/weather/weatherInfo", params=params)
                r.raise_for_status()
            except httpx.HTTPError as e:
                logger.warning("高德天气失败: %s", e)
                return []

        data = r.json()
        if data.get("status") != "1":
            return []

        casts = data.get("casts", [])
        result = []
        for cast in casts:
            try:
                result.append(
                    WeatherDay(
                        date=_date.fromisoformat(cast["date"]),
                        temp_high_c=float(cast["daytemp"]),
                        temp_low_c=float(cast["nighttemp"]),
                        condition=cast.get("dayweather", ""),
                    )
                )
            except (KeyError, ValueError):
                continue
        return result
