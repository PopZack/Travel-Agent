"""Amadeus 工具：机票搜索、酒店搜索、下单。

测试环境（AMADEUS_ENV=test）只搜索，下单返回模拟 PNR，不扣款。
生产环境需自行申请 Amadeus 生产授权。
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from amadeus import Client, ResponseError

from app.tools.cache import cached
from app.common.config import get_settings
from app.tools.models import FlightOffer, HotelOffer, Quote

logger = logging.getLogger(__name__)


class AmadeusTool:
    """封装 Amadeus SDK 的异步友好接口。

    Amadeus SDK 本身是同步的，这里把阻塞调用放在 asyncio.to_thread 里。
    """

    def __init__(self) -> None:
        s = get_settings()
        self._env = s.amadeus_env
        if not s.amadeus_client_id or not s.amadeus_client_secret:
            self._client = None
            logger.info("Amadeus 未配置，机酒搜索与预订将跳过。")
            return
        self._client = Client(
            client_id=s.amadeus_client_id,
            client_secret=s.amadeus_client_secret,
            hostname="production" if s.amadeus_env == "prod" else "test",
        )

    # ---------- 搜索 ----------

    @cached(ttl_seconds=600)  # 10 分钟缓存
    async def search_flights(
        self,
        origin_iata: str,
        dest_iata: str,
        depart_date: date,
        adults: int = 1,
        max_price_cny: float | None = None,
    ) -> list[FlightOffer]:
        if not self._client:
            return []
        import asyncio

        def _do() -> list[FlightOffer]:
            try:
                resp = self._client.shopping.flight_offers_search.get(
                    originLocationCode=origin_iata,
                    destinationLocationCode=dest_iata,
                    departureDate=depart_date.isoformat(),
                    adults=adults,
                    max=20,
                    currencyCode="CNY",
                )
            except ResponseError as e:
                logger.warning("Amadeus flight search failed: %s", e)
                return []
            return [self._parse_flight(o) for o in resp.data]

        offers = await asyncio.to_thread(_do)
        if max_price_cny:
            offers = [o for o in offers if o.price_cny <= max_price_cny]
        return offers

    @cached(ttl_seconds=600)
    async def search_hotels(
        self,
        city_code: str,
        check_in: date,
        check_out: date,
        adults: int = 1,
        max_price_cny: float | None = None,
    ) -> list[HotelOffer]:
        if not self._client:
            return []
        import asyncio

        def _do() -> list[HotelOffer]:
            try:
                # 先查酒店列表
                hotel_list = self._client.reference_data.locations.hotels.by_city.get(
                    cityCode=city_code
                )
                hotel_ids = [h["hotelId"] for h in hotel_list.data][:20]
                if not hotel_ids:
                    return []
                offers_resp = self._client.shopping.hotel_offers_search.get(
                    hotelIds=",".join(hotel_ids),
                    checkInDate=check_in.isoformat(),
                    checkOutDate=check_out.isoformat(),
                    adults=adults,
                    currencyCode="CNY",
                )
            except ResponseError as e:
                logger.warning("Amadeus hotel search failed: %s", e)
                return []
            return [self._parse_hotel(o) for o in offers_resp.data]

        offers = await asyncio.to_thread(_do)
        if max_price_cny:
            offers = [o for o in offers if o.total_cny <= max_price_cny]
        return offers

    # ---------- 下单 ----------

    async def create_order(self, quote: Quote) -> dict:
        """根据报价下单。

        test 模式：返回模拟 PNR，不调真实下单接口。
        prod 模式：调 Flight Create Order + Hotel Booking，返回真实确认码。
        """
        if not self._client:
            return {
                "success": False,
                "error": "Amadeus 未配置，无法下单。请在 .env 填入 AMADEUS_CLIENT_ID/SECRET。",
            }
        if self._env == "test":
            return {
                "success": True,
                "pnr": "MOCKPNR",
                "confirmation_codes": ["MOCK-HTL-001"],
                "simulated": True,
                "total_paid_cny": quote.total_cny,
                "booked_at": datetime.now(timezone.utc).isoformat(),
            }

        # prod 模式：真实下单
        # 注意：完整下单需先确认价格 offer id 仍有效，再 create order。
        # 这里给出骨架；真实实现需保存 search 时的 offer id。
        raise NotImplementedError(
            "生产环境下单需先缓存 search offer id 并实现 price confirm + create order 流程。"
            "请参考 Amadeus 文档补全，或先用 test 模式验证流程。"
        )

    # ---------- 解析 ----------

    def _parse_flight(self, offer: dict) -> FlightOffer:
        seg = offer["itineraries"][0]["segments"][0]
        price = float(offer["price"]["total"])
        return FlightOffer(
            airline=seg.get("carrierCode", ""),
            flight_number=f"{seg.get('carrierCode','')}{seg.get('number','')}",
            depart_time=datetime.fromisoformat(seg["departure"]["at"]),
            arrive_time=datetime.fromisoformat(seg["arrival"]["at"]),
            origin_iata=seg["departure"]["iataCode"],
            dest_iata=seg["arrival"]["iataCode"],
            price_cny=price,
            stops=len(offer["itineraries"][0]["segments"]) - 1,
            deep_link=offer.get("deepLink"),
        )

    def _parse_hotel(self, offer: dict) -> HotelOffer:
        hotel = offer.get("hotel", {})
        total = float(offer["price"]["total"])
        nights = (
            (date.fromisoformat(offer["checkOutDate"]) - date.fromisoformat(offer["checkInDate"])).days
            or 1
        )
        return HotelOffer(
            name=hotel.get("name", ""),
            stars=hotel.get("rating"),
            check_in=date.fromisoformat(offer["checkInDate"]),
            check_out=date.fromisoformat(offer["checkOutDate"]),
            price_per_night_cny=total / nights,
            total_cny=total,
            location=hotel.get("address", {}).get("cityName"),
            deep_link=offer.get("deepLink"),
        )
