from __future__ import annotations

from collections.abc import Iterable

import streamlit as st

from agent_dungeon.forge.forge_terminal_ui import clear_terminal_session

_FORGE_CHALLENGE_SESSION_SUFFIXES = (
    "_code",
    "_stdout",
    "_awaiting_collapse",
    "_collapse",
)


def clear_forge_level_session(key_prefix: str, challenge_ids: Iterable[str]) -> None:
    """清除 Skill Forge 編輯器在 st.session_state 的快取（不含登入／聊天）。"""
    st.session_state.pop(f"{key_prefix}_stdin", None)
    clear_terminal_session(f"{key_prefix}_lab_terminal")
    for challenge_id in challenge_ids:
        clear_terminal_session(f"{key_prefix}_{challenge_id}_terminal")
        for suffix in _FORGE_CHALLENGE_SESSION_SUFFIXES:
            st.session_state.pop(f"{key_prefix}_{challenge_id}{suffix}", None)
