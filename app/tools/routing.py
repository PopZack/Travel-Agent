"""OSRM 路线工具：算两点间驾车距离与时长。"""

from __future__ import annotations

import logging

import httpx

from app.tools.cache import cached
from app.common.config import get_settings
from app.tools.models import RouteSegment

logger = logging.getLogger(__name__)


class RoutingTool:
    def __init__(self) -> None:
        self._base = get_settings().osrm_base_url.rstrip("/")

    @cached(ttl_seconds=86400)  # 路线 1 天缓存
    async def route(
        self,
        from_name: str,
        to_name: str,
        from_coord: tuple[float, float],
        to_coord: tuple[float, float],
        mode: str = "drive",
    ) -> RouteSegment | None:
        """查单段路线。mode=drive/walk/transit（OSRM 公共实例只支持 drive）。"""
        if mode != "drive":
            # 步行/公交用直线距离估算
            return self._estimate(from_name, to_name, from_coord, to_coord, mode)

        url = f"{self._base}/route/v1/driving/{from_coord[1]},{from_coord[0]};{to_coord[1]},{to_coord[0]}"
        async with httpx.AsyncClient(timeout=10) as c:
            try:
                r = await c.get(url, params={"overview": "false"})
                r.raise_for_status()
            except httpx.HTTPError as e:
                logger.warning("OSRM failed: %s", e)
                return None

        data = r.json()
        routes = data.get("routes", [])
        if not routes:
            return None
        leg = routes[0]
        return RouteSegment(
            from_name=from_name,
            to_name=to_name,
            distance_km=round(leg["distance"] / 1000, 1),
            duration_min=round(leg["duration"] / 60, 1),
            mode="drive",  # type: ignore[arg-type]
        )

    def _estimate(
        self,
        from_name: str,
        to_name: str,
        a: tuple[float, float],
        b: tuple[float, float],
        mode: str,
    ) -> RouteSegment:
        """Haversine 直线距离 + 经验速度估算。"""
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
