"""旅行 Agent — Streamlit Web 界面。

运行：
    streamlit run app/streamlit_app.py

功能：
- 对话框输入旅行需求
- LLM 生成过程实时流式输出（逐字显示）
- 展示按天行程卡片
- 报价确认按钮（human-in-the-loop）
- 下单结果展示
"""

from __future__ import annotations

import uuid

import streamlit as st

from travel_agent.memory import load_preferences, save_trip
from travel_agent.streaming import run_streaming

st.set_page_config(page_title="旅行 Agent", page_icon="✈️", layout="wide")


def render_itinerary(itinerary) -> None:
    """渲染按天行程卡片。"""
    if not itinerary or not itinerary.days:
        st.info("暂无行程")
        return
    for day in itinerary.days:
        with st.expander(f"第 {day.day} 天 — {day.date}　💰 {day.daily_cost_cny:.0f} 元", expanded=True):
            if day.hotel:
                st.markdown(f"🏨 **住宿**：{day.hotel}")
            for act in day.activities:
                st.markdown(
                    f"- `{act.time_start}–{act.time_end}` **{act.place.name}**"
                    f"{'　' + act.note if act.note else ''}"
                    f"{'　💰' + f'{act.cost_cny:.0f}' if act.cost_cny else ''}"
                )
            if day.transit:
                st.caption(" → ".join(f"{t.from_name}→{t.to_name}({t.duration_min:.0f}分钟)" for t in day.transit))
    st.markdown(f"### 💰 总计：{itinerary.total_cost_cny:.0f} 元")


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
            # 状态行（实时更新"正在解析…""正在编排…"）
            status_box = st.empty()
            # LLM 流式输出区
            stream_box = st.empty()

            current_status = ""

            def on_status(msg: str) -> None:
                nonlocal current_status
                current_status = msg
                status_box.markdown(f"**{msg}**")

            def on_chunk(chunk: str) -> None:
                # 追加到流式区（用 markdown 实时拼接）
                pass  # 用 st.write_stream 更好，见下方

            # 用 st.write_stream 包装 LLM 流式输出
            # 但 run_streaming 是同步函数，内部调 on_chunk
            # 改用：直接调 run_streaming，on_chunk 往 stream_box 追加
            collected = []

            def on_chunk_collect(chunk: str) -> None:
                collected.append(chunk)
                # 实时显示当前 LLM 输出（JSON 原文，让用户看到在生成）
                stream_box.code("".join(collected), language="json")

            state = run_streaming(query, on_chunk_collect, on_status)

            # 清掉流式 JSON 原文（太长不好看），换成状态完成提示
            stream_box.empty()
            status_box.markdown(f"**✅ {current_status}**")

            status = state.get("status")

            if status == "awaiting_confirm":
                st.divider()
                if state.get("itinerary"):
                    render_itinerary(state["itinerary"])
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
    if state.get("itinerary"):
        save_trip(
            st.session_state.get("user_id", "default"),
            query,
            state["itinerary"].model_dump(mode="json"),
        )


if __name__ == "__main__":
    main()
