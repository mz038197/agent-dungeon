from __future__ import annotations

from pathlib import Path

import streamlit as st

from agent_dungeon.forge.agent_terminal import (
    AgentTerminalSession,
    TerminalState,
    is_running,
    poll_output,
    send_input,
    start_agent,
    stop_agent,
)

_SESSION_KEY = "forge_terminal_session"
_OUTPUT_KEY = "forge_terminal_output"


def _session_state_key(base: str, session_key: str) -> str:
    return f"{session_key}_{base}"


def get_terminal_session(session_key: str) -> AgentTerminalSession | None:
    raw = st.session_state.get(_session_state_key(_SESSION_KEY, session_key))
    return raw if isinstance(raw, AgentTerminalSession) else None


def clear_terminal_session(session_key: str) -> None:
    existing = get_terminal_session(session_key)
    if existing is not None:
        stop_agent(existing)
    st.session_state.pop(_session_state_key(_SESSION_KEY, session_key), None)
    st.session_state.pop(_session_state_key(_OUTPUT_KEY, session_key), None)


def render_agent_terminal(
    *,
    session_key: str,
    agent_py: Path,
    google_sub: str,
    disabled: bool = False,
) -> AgentTerminalSession | None:
    st.markdown("**Agent 終端機**")
    st.caption("啟動後一行一行輸入；`bye` 優雅離開，或 ⏹ 等同 Ctrl+C 強制結束。")

    session = get_terminal_session(session_key)
    if session is not None:
        poll_output(session)
        st.session_state[_session_state_key(_OUTPUT_KEY, session_key)] = session.effective_output()

    output = str(st.session_state.get(_session_state_key(_OUTPUT_KEY, session_key), ""))
    st.code(output or "（尚未啟動）", language="text")

    if session is not None and session.state == TerminalState.EXITED:
        st.caption(f"Agent 已結束（turns={session.turn_count}，exit={session.exit_code}）")
    elif session is not None and is_running(session):
        st.caption(f"執行中 · 已對話 {session.turn_count} 輪（不含 bye）")

    ctrl = st.columns([2, 2, 3])
    with ctrl[0]:
        if st.button(
            "▶ 啟動 Agent",
            key=f"{session_key}_start",
            disabled=disabled or (session is not None and is_running(session)),
            use_container_width=True,
            type="primary",
        ):
            clear_terminal_session(session_key)
            session = start_agent(agent_py, google_sub=google_sub)
            st.session_state[_session_state_key(_SESSION_KEY, session_key)] = session
            st.rerun()
    with ctrl[1]:
        if st.button(
            "⏹ 結束 Agent（Ctrl+C）",
            key=f"{session_key}_stop",
            disabled=disabled or session is None or not is_running(session),
            use_container_width=True,
        ):
            if session is not None:
                stop_agent(session)
                poll_output(session)
                st.session_state[_session_state_key(_OUTPUT_KEY, session_key)] = session.effective_output()
            st.rerun()

    with ctrl[2]:
        line = st.text_input(
            "輸入訊息",
            key=f"{session_key}_input_line",
            disabled=disabled or session is None or not is_running(session),
            placeholder="輸入後按 Enter 或按送出",
        )
        if st.button(
            "送出",
            key=f"{session_key}_send",
            disabled=disabled
            or session is None
            or not is_running(session)
            or not str(line).strip(),
            use_container_width=True,
        ):
            send_input(session, str(line))
            st.session_state[_session_state_key(_OUTPUT_KEY, session_key)] = ""
            st.rerun()

    return get_terminal_session(session_key)
