"""Google Places 工具：景点与餐厅搜索。"""

from __future__ import annotations

import logging

try:
    import googlemaps
    _HAS_GOOGLEMAPS = True
except ImportError:
    _HAS_GOOGLEMAPS = False
    googlemaps = None  # type: ignore

from app.tools.cache import cached
from app.common.config import get_settings
from app.tools.models import Place

logger = logging.getLogger(__name__)


class PlacesTool:
    def __init__(self) -> None:
        s = get_settings()
        if not _HAS_GOOGLEMAPS:
            self._gmaps = None
            logger.info("googlemaps SDK 未安装，Google Places 搜索将跳过。")
            return
        try:
            self._gmaps = googlemaps.Client(key=s.google_places_api_key)
        except ValueError as e:
            logger.warning("Google Places key 无效，景点/餐厅搜索将跳过：%s", e)
            self._gmaps = None

    @cached(ttl_seconds=3600)  # 景点 1 小时缓存
    async def search_attractions(self, location: str, limit: int = 15) -> list[Place]:
        if not self._gmaps:
            return []
        import asyncio

        def _do() -> list[Place]:
            try:
                resp = self._gmaps.places(
                    query=f"{location} 景点 tourist attractions",
                    language="zh-CN",
                )
            except Exception as e:
                logger.warning("Google Places attractions failed: %s", e)
                return []
            return [self._parse(p, "attraction") for p in resp.get("results", [])[:limit]]

        return await asyncio.to_thread(_do)

    @cached(ttl_seconds=3600)
    async def search_restaurants(self, location: str, limit: int = 15) -> list[Place]:
        if not self._gmaps:
            return []
        import asyncio

        def _do() -> list[Place]:
            try:
                resp = self._gmaps.places(
                    query=f"{location} 餐厅 restaurant",
                    language="zh-CN",
                )
            except Exception as e:
                logger.warning("Google Places restaurants failed: %s", e)
                return []
            return [self._parse(p, "restaurant") for p in resp.get("results", [])[:limit]]

        return await asyncio.to_thread(_do)

    def _parse(self, p: dict, category: str) -> Place:
        geo = p.get("geometry", {}).get("location", {})
        return Place(
            name=p.get("name", ""),
            category=category,  # type: ignore[arg-type]
            rating=p.get("rating"),
            address=p.get("formatted_address") or p.get("vicinity"),
            lat=geo.get("lat"),
            lng=geo.get("lng"),
            price_level=p.get("price_level"),
        )
