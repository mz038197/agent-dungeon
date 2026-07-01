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
    brain_challenge_codes: dict[str, str] | None = None,
    brain_lab_code: str = "",
    agent_py_path: str | None = None,
) -> None:
    preview = build_agent_py_preview(
        progress,
        challenge_codes=challenge_codes,
        lab_code=lab_code,
        brain_challenge_codes=brain_challenge_codes,
        brain_lab_code=brain_lab_code,
        agent_py_path=agent_py_path,
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
    brain_challenge_codes: dict[str, str] | None = None,
    brain_lab_code: str = "",
    agent_py_path: str | None = None,
) -> None:
    _render_agent_py_preview(
        progress,
        challenge_codes=challenge_codes,
        lab_code=lab_code,
        brain_challenge_codes=brain_challenge_codes,
        brain_lab_code=brain_lab_code,
        agent_py_path=agent_py_path,
    )
    render_chat_panel(extra_context=extra_context, page_name=page_name)
