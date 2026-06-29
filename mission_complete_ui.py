from __future__ import annotations

import html

import streamlit as st

from shell_ui import navigation_page_path


def render_mission_complete_banner(
    *,
    message: str,
    next_level_label: str,
    next_level_icon: str,
    next_page: str | None = None,
    button_key: str,
) -> None:
    safe_message = html.escape(message)
    safe_label = html.escape(next_level_label)
    can_navigate = bool(next_page)

    left, right = st.columns([3, 1], vertical_alignment="center")
    with left:
        st.markdown(
            f"""
<div class="mission-complete-banner-v2">
  <span class="mission-complete-trophy">🏆</span>
  <div class="mission-complete-body">
    <div class="mission-complete-title">MISSION COMPLETE!</div>
    <div class="mission-complete-msg">{safe_message}</div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            f"""
<div class="mission-complete-next">
  <div class="mission-complete-next-label">下一個關卡：{safe_label}</div>
  <div class="mission-complete-next-icon">{html.escape(next_level_icon)}</div>
</div>
""",
            unsafe_allow_html=True,
        )
        if st.button("→", disabled=not can_navigate, key=button_key, use_container_width=True):
            if next_page:
                st.switch_page(navigation_page_path(next_page))
