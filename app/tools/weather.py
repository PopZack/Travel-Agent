"""OpenWeather 工具：查天气预报。"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

import httpx

from app.tools.cache import cached
from app.common.config import get_settings
from app.tools.models import WeatherDay

logger = logging.getLogger(__name__)

# OpenWeather condition code → 中文
_COND_MAP = {
    "Clear": "晴",
    "Clouds": "多云",
    "Rain": "雨",
    "Drizzle": "小雨",
    "Thunderstorm": "雷雨",
    "Snow": "雪",
    "Mist": "薄雾",
    "Fog": "雾",
    "Haze": "霾",
}


class WeatherTool:
    BASE = "https://api.openweathermap.org/data/2.5"

    def __init__(self) -> None:
        self._key = get_settings().openweather_api_key

    @cached(ttl_seconds=1800)  # 30 分钟缓存
    async def forecast(self, lat: float, lng: float, days: int = 7) -> list[WeatherDay]:
        """查未来 N 天预报（OpenWeather 免费层给 5 天，付费 16 天）。"""
        async with httpx.AsyncClient(timeout=10) as c:
            try:
                r = await c.get(
                    f"{self.BASE}/forecast",
                    params={
                        "lat": lat,
                        "lon": lng,
                        "appid": self._key,
                        "units": "metric",
                        "cnt": min(days * 8, 40),
                        "lang": "zh_cn",
                    },
                )
                r.raise_for_status()
            except httpx.HTTPError as e:
                logger.warning("OpenWeather failed: %s", e)
                return []

        return self._aggregate(r.json())

    def _aggregate(self, data: dict) -> list[WeatherDay]:
        """把 3 小时间隔的数据按天聚合。"""
        by_day: dict[date, list[dict]] = {}
        for item in data.get("list", []):
            d = datetime.fromisoformat(item["dt_txt"]).date()
            by_day.setdefault(d, []).append(item)

        out: list[WeatherDay] = []
        for d, items in sorted(by_day.items()):
            temps = [i["main"]["temp"] for i in items]
            conds = [i["weather"][0]["main"] for i in items]
            # 取出现最多的天气
            cond = max(set(conds), key=conds.count)
            out.append(
                WeatherDay(
                    date=d,
                    temp_high_c=max(temps),
                    temp_low_c=min(temps),
                    condition=_COND_MAP.get(cond, cond),
                    precip_prob=max((i.get("pop", 0) for i in items), default=0.0),
                )
            )
        return out
