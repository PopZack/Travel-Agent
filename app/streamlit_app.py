"""旅行 Agent — Streamlit Web 界面。

运行：
    streamlit run app/streamlit_app.py

功能：
- 对话框输入旅行需求
- 友好进度条（不显示原始 JSON）
- 按天行程卡片 + 天气 + 地图链接
- 报价确认按钮（human-in-the-loop）
- 下单结果展示
"""

from __future__ import annotations

import uuid

import streamlit as st

from travel_agent.memory import list_trips, load_preferences, save_preferences, save_trip
from travel_agent.streaming import run_streaming

st.set_page_config(page_title="旅行 Agent", page_icon="✈️", layout="wide")

# 进度步骤
_STEPS = ["🔍 解析意图", "🌐 搜索数据", "📅 编排行程", "💰 生成报价"]


def render_progress(current_step: int, status_text: str) -> None:
    """渲染进度条。"""
    progress = st.progress(0)
    cols = st.columns(len(_STEPS))
    for i, (col, label) in enumerate(zip(cols, _STEPS)):
        if i < current_step:
            col.markdown(f"✅ {label}")
        elif i == current_step:
            col.markdown(f"🔄 {label}")
        else:
            col.markdown(f"⬜ {label}")
    if current_step < len(_STEPS):
        progress.progress((current_step + 1) / len(_STEPS))
    return progress


def render_itinerary(itinerary, weather=None, visa_info=None) -> None:
    """渲染按天行程卡片。"""
    if not itinerary or not itinerary.days:
        st.info("暂无行程")
        return

    # 签证提醒
    if visa_info:
        st.warning(f"🛂 **签证提醒**：{visa_info}")

    # 天气总览
    if weather:
        with st.expander("🌤️ 天气预报", expanded=False):
            cols = st.columns(min(len(weather), 7))
            for i, w in enumerate(weather[:7]):
                if i < len(cols):
                    with cols[i]:
                        st.markdown(f"**{w.date}**")
                        st.markdown(f"{w.condition}")
                        st.caption(f"{w.temp_low_c:.0f}~{w.temp_high_c:.0f}°C")

    for day in itinerary.days:
        with st.expander(f"📅 第 {day.day} 天 — {day.date}　💰 {day.daily_cost_cny:.0f} 元", expanded=True):
            if day.hotel:
                st.markdown(f"🏨 **住宿**：{day.hotel}")

            # 活动列表
            for act in day.activities:
                icon = _category_icon(act.place.category)
                cost = f"　💰 {act.cost_cny:.0f}" if act.cost_cny else ""
                note = f"　{act.note}" if act.note else ""
                st.markdown(
                    f"{icon} `{act.time_start}–{act.time_end}` **{act.place.name}**{note}{cost}"
                )
                # 高德地图链接
                if act.place.lat and act.place.lng:
                    url = f"https://uri.amap.com/marker?position={act.place.lng},{act.place.lat}&name={act.place.name}"
                    st.caption(f"📍 [在高德地图中查看]({url})")

            if day.transit:
                st.caption("🚗 " + " → ".join(f"{t.from_name}→{t.to_name}({t.duration_min:.0f}分钟)" for t in day.transit))

    st.markdown(f"### 💰 总计：{itinerary.total_cost_cny:.0f} 元")


def _category_icon(category: str) -> str:
    """根据活动类型返回图标。"""
    c = (category or "").lower()
    if "restaurant" in c or "餐" in c:
        return "🍽️"
    if "hotel" in c or "住宿" in c:
        return "🏨"
    if "transport" in c or "交通" in c:
        return "🚗"
    return "📍"


def render_quote(quote) -> None:
    """渲染报价表。"""
    st.subheader("📋 报价单")
    for i, item in enumerate(quote.items, 1):
        refund = "✅可退" if item.refundable else "❌不可退"
        st.markdown(
            f"{i}. **[{item.type}]** {item.description}　"
            f"💰 {item.price_cny:.0f} 元　{refund}"
        )
        if item.cancel_policy:
            st.caption(item.cancel_policy)
    st.markdown(f"### 合计：{quote.total_cny:.0f} 元")
    if quote.expires_at:
        st.caption(f"报价有效期至：{quote.expires_at:%Y-%m-%d %H:%M}")


def main() -> None:
    st.title("✈️ 旅行 Agent")
    st.caption("自然语言 → 行程规划 → 人工确认 → 预订下单")

    user_id = st.session_state.get("user_id", "default")
    prefs = load_preferences(user_id)
    if prefs:
        st.sidebar.info(f"已载入偏好：{prefs}")

    # 历史行程
    with st.sidebar:
        st.subheader("📜 历史行程")
        trips = list_trips(user_id, limit=5)
        if trips:
            for t in trips:
                with st.expander(f"#{t['id']} {t['query'][:20]}", expanded=False):
                    st.caption(f"创建于 {t['created_at']}")
        else:
            st.caption("暂无历史行程")

    # 对话历史
    if "messages" not in st.session_state:
        st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # 输入
    if query := st.chat_input("描述你的旅行计划…"):
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        with st.chat_message("assistant"):
            # 进度区
            progress_container = st.container()
            # 流式文字区（像 DeepSeek 那样逐字显示）
            stream_area = st.empty()
            step_map = {"解析": 0, "搜索": 1, "编排": 2, "报价": 3, "完成": 4}
            current_step = 0

            with progress_container:
                step_boxes = st.columns(len(_STEPS))
                status_line = st.empty()

            def on_status(msg: str) -> None:
                nonlocal current_step
                for key, idx in step_map.items():
                    if key in msg:
                        current_step = idx
                        break
                for i, (box, label) in enumerate(zip(step_boxes, _STEPS)):
                    if i < current_step:
                        box.markdown(f"✅ {label}")
                    elif i == current_step:
                        box.markdown(f"🔄 {label}")
                    else:
                        box.markdown(f"⬜ {label}")
                status_line.caption(msg)

            # 逐字追加显示（DeepSeek 风格）
            displayed = []

            def on_chunk(chunk: str) -> None:
                displayed.append(chunk)
                stream_area.markdown("".join(displayed))

            state = run_streaming(query, on_chunk, on_status)

            # 清掉流式文字，后面用卡片展示
            stream_area.empty()

            # 完成进度
            for i, (box, label) in enumerate(zip(step_boxes, _STEPS)):
                box.markdown(f"✅ {label}")
            status_line.empty()

            status = state.get("status")

            if status == "awaiting_confirm":
                st.divider()
                if state.get("itinerary"):
                    research = state.get("research")
                    weather_data = research.weather if research else None
                    visa_data = research.visa_info if research else None
                    render_itinerary(state["itinerary"], weather_data, visa_data)
                if state.get("quote"):
                    render_quote(state["quote"])
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ 确认预订", type="primary"):
                            with st.spinner("正在下单…"):
                                _do_booking(state, query)
                    with col2:
                        if st.button("✏️ 修改"):
                            st.session_state.messages.append(
                                {"role": "assistant", "content": "请告诉我你想调整什么。"}
                            )
                            st.rerun()
            elif status == "error":
                st.error(state.get("error", "未知错误"))
            else:
                if state.get("itinerary"):
                    render_itinerary(state["itinerary"])


def _do_booking(state: dict, query: str) -> None:
    """模拟下单（test 模式）。"""
    from datetime import datetime, timezone

    from travel_agent.models import BookingResult

    quote = state.get("quote")
    if not quote:
        st.warning("无报价")
        return
    result = BookingResult(
        success=True,
        pnr="MOCKPNR",
        confirmation_codes=["MOCK-001"],
        total_paid_cny=quote.total_cny,
        simulated=True,
        booked_at=datetime.now(timezone.utc),
    )
    st.success(
        f"🎉 预订成功！PNR: {result.pnr}　"
        f"确认码: {', '.join(result.confirmation_codes)}　"
        f"支付: {result.total_paid_cny:.0f} 元（模拟，未真实扣款）"
    )
    user_id = st.session_state.get("user_id", "default")
    if state.get("itinerary"):
        save_trip(
            user_id,
            query,
            state["itinerary"].model_dump(mode="json"),
        )
        # 从意图提取偏好并保存
        intent = state.get("intent")
        if intent:
            prefs = {
                "destination": intent.destination,
                "styles": [s.value for s in intent.styles],
                "adults": intent.adults,
                "children": intent.children,
            }
            save_preferences(user_id, prefs)


if __name__ == "__main__":
    main()
