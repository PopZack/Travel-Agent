"""后处理测试：build_quote 与 fill_transit。"""

from datetime import date, datetime, time, timezone

import pytest

from travel_agent.models import (
    Activity,
    DayPlan,
    FlightOffer,
    HotelOffer,
    Itinerary,
    Place,
    Quote,
    ResearchResult,
)
from travel_agent.postprocess import build_quote


def _make_itinerary() -> Itinerary:
    return Itinerary(
        days=[
            DayPlan(
                day=1,
                date=date(2026, 11, 1),
                activities=[
                    Activity(
                        time_start=time(9, 0),
                        time_end=time(11, 0),
                        place=Place(name="清水寺", category="attraction"),
                        cost_cny=20,
                    ),
                    Activity(
                        time_start=time(12, 0),
                        time_end=time(13, 0),
                        place=Place(name="京都拉面", category="restaurant"),
                        cost_cny=100,
                    ),
                ],
                hotel="京都酒店",
                daily_cost_cny=1120,
            ),
        ],
        total_cost_cny=1120,
    )


def _make_research() -> ResearchResult:
    return ResearchResult(
        flights=[
            FlightOffer(
                airline="MU",
                flight_number="MU123",
                depart_time=datetime(2026, 11, 1, 8, 0),
                arrive_time=datetime(2026, 11, 1, 12, 0),
                origin_iata="PVG",
                dest_iata="KIX",
                price_cny=3000,
            ),
        ],
        hotels=[
            HotelOffer(
                name="京都酒店",
                stars=4.0,
                check_in=date(2026, 11, 1),
                check_out=date(2026, 11, 4),
                price_per_night_cny=500,
                total_cny=1500,
            ),
        ],
    )


def test_build_quote_with_research():
    """有航班+酒店+活动 → 报价含全部三类。"""
    itinerary = _make_itinerary()
    research = _make_research()
    quote = build_quote(itinerary, research)

    types = [i.type for i in quote.items]
    assert "flight" in types
    assert "hotel" in types
    assert "activity" in types
    # 总价 = 机票 3000 + 酒店 1500 + 活动 20 + 活动 100
    assert quote.total_cny == 4620


def test_build_quote_without_research():
    """无研究结果 → 只有活动费用。"""
    itinerary = _make_itinerary()
    quote = build_quote(itinerary, None)

    assert all(i.type == "activity" for i in quote.items)
    assert quote.total_cny == 120  # 20 + 100


def test_build_quote_picks_cheapest_flight():
    """多航班 → 选最便宜。"""
    itinerary = _make_itinerary()
    research = _make_research()
    research.flights.append(
        FlightOffer(
            airline="JL",
            flight_number="JL456",
            depart_time=datetime(2026, 11, 1, 9, 0),
            arrive_time=datetime(2026, 11, 1, 13, 0),
            origin_iata="PVG",
            dest_iata="KIX",
            price_cny=2000,
        )
    )
    quote = build_quote(itinerary, research)
    flight_item = next(i for i in quote.items if i.type == "flight")
    assert flight_item.price_cny == 2000


def test_build_quote_has_expiry():
    """报价有有效期。"""
    quote = build_quote(_make_itinerary(), None)
    assert quote.expires_at is not None


def test_build_quote_zero_cost_activities_skipped():
    """cost_cny=0 的活动不进报价。"""
    itinerary = Itinerary(
        days=[
            DayPlan(
                day=1,
                date=date(2026, 11, 1),
                activities=[
                    Activity(
                        time_start=time(9, 0),
                        time_end=time(10, 0),
                        place=Place(name="免费景点"),
                        cost_cny=0,
                    ),
                    Activity(
                        time_start=time(11, 0),
                        time_end=time(12, 0),
                        place=Place(name="收费景点"),
                        cost_cny=50,
                    ),
                ],
            ),
        ],
        total_cost_cny=50,
    )
    quote = build_quote(itinerary, None)
    assert len(quote.items) == 1
    assert quote.items[0].price_cny == 50
