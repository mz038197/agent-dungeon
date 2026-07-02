from __future__ import annotations

import streamlit as st

from agent_dungeon.agent.agent_panel import render_chat_panel
from agent_dungeon.agent.agent_py_preview import build_agent_py_preview
from agent_dungeon.core.progress import DungeonProgress


def _render_agent_py_preview(
    progress: DungeonProgress,
    *,
    agent_py_path: str | None = None,
    google_sub: str | None = None,
) -> None:
    preview = build_agent_py_preview(
        progress,
        agent_py_path=agent_py_path,
        google_sub=google_sub,
    )
    st.markdown("**agent.py（建造中）**")
    st.code(preview, language="python")


def render_agent_column(
    *,
    progress: DungeonProgress,
    extra_context: str = "",
    page_name: str = "",
    agent_py_path: str | None = None,
    google_sub: str | None = None,
) -> None:
    _render_agent_py_preview(
        progress,
        agent_py_path=agent_py_path,
        google_sub=google_sub,
    )
    render_chat_panel(extra_context=extra_context, page_name=page_name)
