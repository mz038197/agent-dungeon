from __future__ import annotations

import streamlit as st

from agent_dungeon.agent.agent_panel import render_chat_panel
from agent_dungeon.agent.agent_py_preview import build_agent_py_preview
from agent_dungeon.core.progress import DungeonProgress


def _render_agent_py_preview(
    progress: DungeonProgress,
    *,
    challenge_codes: dict[str, str] | None,
    lab_code: str,
) -> None:
    preview = build_agent_py_preview(
        progress,
        challenge_codes=challenge_codes,
        lab_code=lab_code,
    )
    st.markdown("**agent.py（建造中）**")
    st.code(preview, language="python")


def render_agent_column(
    *,
    progress: DungeonProgress,
    extra_context: str = "",
    page_name: str = "",
    challenge_codes: dict[str, str] | None = None,
    lab_code: str = "",
) -> None:
    _render_agent_py_preview(
        progress,
        challenge_codes=challenge_codes,
        lab_code=lab_code,
    )
    render_chat_panel(extra_context=extra_context, page_name=page_name)
