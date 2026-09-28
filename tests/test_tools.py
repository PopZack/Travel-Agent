"""工具层测试 — 用 respx mock httpx，无需真实 API key。"""

from datetime import date

import httpx
import respx


@respx.mock
async def test_weather_forecast_parses():
    from travel_agent.tools.weather import WeatherTool

    # mock OpenWeather 响应
    respx.get("https://api.openweathermap.org/data/2.5/forecast").respond(
        json={
            "list": [
                {
                    "dt_txt": "2026-11-01 09:00:00",
                    "main": {"temp": 20},
                    "weather": [{"main": "Clear"}],
                    "pop": 0.0,
                },
                {
                    "dt_txt": "2026-11-01 15:00:00",
                    "main": {"temp": 25},
                    "weather": [{"main": "Clouds"}],
                    "pop": 0.1,
                },
            ]
        }
    )

    # 用 monkeypatch 绕过 settings 校验
    import travel_agent.tools.weather as w

    tool = object.__new__(WeatherTool)
    tool._key = "fake"
    days = await tool.forecast(35.0, 135.0, days=1)
    assert len(days) == 1
    assert days[0].temp_high_c == 25
    assert days[0].temp_low_c == 20


@respx.mock
async def test_routing_osrm():
    from travel_agent.tools.routing import RoutingTool

    respx.get("http://router.project-osrm.org/route/v1/driving/135.0,35.0;135.5,35.5").respond(
        json={"routes": [{"distance": 60000, "duration": 3600}]}
    )

    tool = object.__new__(RoutingTool)
    tool._base = "http://router.project-osrm.org"
    seg = await tool.route("A", "B", (35.0, 135.0), (35.5, 135.5))
    assert seg is not None
    assert seg.distance_km == 60.0
    assert seg.duration_min == 60.0


def test_exchange_currency_map():
    from travel_agent.tools.exchange import _DEST_CURRENCY

    assert _DEST_CURRENCY["京都"] == "JPY"
    assert _DEST_CURRENCY["曼谷"] == "THB"


def test_visa_lookup_local_table():
    from travel_agent.tools.visa import VisaTool, _VISA_TABLE

    assert "日本" in _VISA_TABLE
    assert "免签" in _VISA_TABLE["泰国"]
