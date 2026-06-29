from __future__ import annotations

import html
from typing import Literal

import streamlit as st


def render_level_heading(level_num: int, description: str, *, tag: str | None = None) -> None:
    safe_description = html.escape(description)
    st.markdown(f"## 第 {level_num} 關：{safe_description}")
    if tag:
        st.markdown(
            f'<span class="dungeon-level-tag">{html.escape(tag)}</span>',
            unsafe_allow_html=True,
        )


def render_numbered_section_heading(
    number: int,
    title: str,
    *,
    variant: Literal["purple", "blue", "green"] = "blue",
) -> None:
    safe_title = html.escape(title)
    st.markdown(
        f'<div class="dungeon-section-heading dungeon-section-heading--{variant}">'
        f'<span class="dungeon-section-badge">{number}</span>'
        f'<span class="dungeon-section-title">{safe_title}</span>'
        f"</div>",
        unsafe_allow_html=True,
    )
