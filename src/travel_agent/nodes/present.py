"""present 节点：把行程转成报价单，准备展示给用户确认。"""

from __future__ import annotations

from travel_agent.postprocess import build_quote
from travel_agent.state import TravelState


async def present(state: TravelState) -> dict:
    """节点：生成报价。"""
    itinerary = state.get("itinerary")
    research = state.get("research")
    if not itinerary:
        return {"status": "error", "error": "无行程可报价"}

    quote = build_quote(itinerary, research)
    return {"quote": quote, "status": "awaiting_confirm"}
