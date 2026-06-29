from __future__ import annotations

import streamlit as st

from page_shell import page_shell
from shell_ui import format_extra_context, inject_style, load_page_data, save_page_data

PAGE_NAME = "Home"

st.set_page_config(page_title="Home", page_icon="🏠", layout="wide")
inject_style()


def render_main() -> str:
    state = load_page_data(PAGE_NAME)
    nickname = st.text_input("暱稱", value=str(state.get("nickname", "")), placeholder="例如：小明")
    goal = st.text_area("今日目標", value=str(state.get("goal", "")), placeholder="一句話描述今天想完成的事")
    save_page_data(PAGE_NAME, {"nickname": nickname, "goal": goal})
    st.info("改完左欄內容後，可在右欄請 Agent 用暱稱跟你打招呼。")
    return format_extra_context(PAGE_NAME, 暱稱=nickname or "（未填）", 今日目標=goal or "（未填）")


page_shell(
    "Home · 第一關占位",
    "確認左欄狀態能傳到右欄 Agent。",
    render_main,
    page_name=PAGE_NAME,
)
