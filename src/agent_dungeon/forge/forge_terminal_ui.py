from __future__ import annotations

import html
from pathlib import Path
from typing import Literal

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
from agent_dungeon.forge.forge_terminal_html import split_stdout_pending_prompt

_SESSION_KEY = "forge_terminal_session"
_OUTPUT_KEY = "forge_terminal_output"

InputMode = Literal["button", "form"]
LayoutMode = Literal["split", "inline"]

_PROMPT_KEY = "forge_terminal_pending_prompt"
_AWAITING_KEY = "forge_terminal_awaiting_input"

_INLINE_TERMINAL_CSS = """
<style>
.forge-terminal-inline-form [data-testid="column"] {
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}
.forge-terminal-inline-form pre {
  margin: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
}
.forge-terminal-inline-form [data-testid="stFormSubmitButton"] {
  display: none;
}
</style>
"""


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
    st.session_state.pop(_session_state_key(_PROMPT_KEY, session_key), None)
    st.session_state.pop(_session_state_key(_AWAITING_KEY, session_key), None)


def _refresh_terminal_output(session_key: str, session: AgentTerminalSession | None) -> str:
    if session is not None:
        poll_output(session)
        st.session_state[_session_state_key(_OUTPUT_KEY, session_key)] = session.effective_output()
    return str(st.session_state.get(_session_state_key(_OUTPUT_KEY, session_key), ""))


def _submit_terminal_input(
    session: AgentTerminalSession,
    *,
    session_key: str,
    line: str,
) -> None:
    send_input(session, line)
    st.session_state[_session_state_key(_AWAITING_KEY, session_key)] = False
    st.rerun()


def _render_terminal_controls(
    *,
    session_key: str,
    session: AgentTerminalSession | None,
    agent_py: Path,
    google_sub: str,
    disabled: bool,
    start_button_label: str,
    stop_button_label: str,
) -> AgentTerminalSession | None:
    ctrl = st.columns([1, 1])
    with ctrl[0]:
        if st.button(
            start_button_label,
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
            stop_button_label,
            key=f"{session_key}_stop",
            disabled=disabled or session is None or not is_running(session),
            use_container_width=True,
        ):
            if session is not None:
                stop_agent(session)
                poll_output(session)
                st.session_state[_session_state_key(_OUTPUT_KEY, session_key)] = session.effective_output()
            st.rerun()
    return get_terminal_session(session_key)


def _render_prompt_input_inline(
    *,
    session_key: str,
    session: AgentTerminalSession,
    prompt: str,
    disabled: bool,
) -> None:
    input_disabled = disabled or not is_running(session)

    st.markdown('<div class="forge-terminal-inline-form">', unsafe_allow_html=True)
    with st.form(key=f"{session_key}_inline_form", clear_on_submit=True, border=False):
        if prompt:
            prompt_col, input_col = st.columns([1, 3], gap="small", vertical_alignment="center")
            with prompt_col:
                st.markdown(f"<pre>{html.escape(prompt)}</pre>", unsafe_allow_html=True)
            with input_col:
                line = st.text_input(
                    "輸入",
                    key=f"{session_key}_input_line",
                    disabled=input_disabled,
                    label_visibility="collapsed",
                    placeholder="在此輸入…",
                )
        else:
            line = st.text_input(
                "輸入",
                key=f"{session_key}_input_line",
                disabled=input_disabled,
                placeholder="輸入後按 Enter 送出",
                label_visibility="collapsed",
            )
        submitted = st.form_submit_button("送出", disabled=input_disabled)
    st.markdown("</div>", unsafe_allow_html=True)

    if submitted and str(line).strip():
        _submit_terminal_input(session, session_key=session_key, line=str(line))


def _render_split_input_area(
    *,
    session_key: str,
    session: AgentTerminalSession | None,
    disabled: bool,
    input_mode: InputMode,
) -> None:
    input_disabled = disabled or session is None or not is_running(session)

    if input_mode == "form":
        with st.form(key=f"{session_key}_input_form", clear_on_submit=True):
            line = st.text_input(
                "輸入訊息",
                key=f"{session_key}_input_line",
                disabled=input_disabled,
                placeholder="輸入後按 Enter 送出",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button(
                "送出",
                disabled=input_disabled,
                use_container_width=True,
            )
        if submitted and session is not None and str(line).strip():
            _submit_terminal_input(session, session_key=session_key, line=str(line))
        return

    line = st.text_input(
        "輸入訊息",
        key=f"{session_key}_input_line",
        disabled=input_disabled,
        placeholder="輸入後按 Enter 或按送出",
    )
    if st.button(
        "送出",
        key=f"{session_key}_send",
        disabled=input_disabled or not str(line).strip(),
        use_container_width=True,
    ):
        if session is not None:
            _submit_terminal_input(session, session_key=session_key, line=str(line))


def _render_inline_terminal_panel(
    *,
    session_key: str,
    disabled: bool,
) -> None:
    session = get_terminal_session(session_key)
    output = _refresh_terminal_output(session_key, session)
    running = session is not None and is_running(session)
    completed, prompt = split_stdout_pending_prompt(output, awaiting_input=running)

    awaiting_key = _session_state_key(_AWAITING_KEY, session_key)
    prompt_key = _session_state_key(_PROMPT_KEY, session_key)

    if not running:
        st.session_state[awaiting_key] = False
        st.session_state[prompt_key] = ""

    if running and prompt.strip():
        st.session_state[prompt_key] = prompt
        if not st.session_state.get(awaiting_key):
            st.session_state[awaiting_key] = True
            st.rerun()
    elif running and not prompt.strip():
        st.session_state[awaiting_key] = False

    awaiting_input = bool(running and st.session_state.get(awaiting_key) and prompt.strip())
    poll_interval = None if awaiting_input else (0.2 if running else None)
    display_prompt = str(st.session_state.get(prompt_key, ""))

    with st.container(border=True):
        @st.fragment(run_every=poll_interval)
        def _live_output() -> None:
            live_session = get_terminal_session(session_key)
            live_output = _refresh_terminal_output(session_key, live_session)
            live_running = live_session is not None and is_running(live_session)
            live_completed, live_prompt = split_stdout_pending_prompt(
                live_output,
                awaiting_input=live_running,
            )

            if live_running and live_prompt.strip():
                st.session_state[prompt_key] = live_prompt
                if not st.session_state.get(awaiting_key):
                    st.session_state[awaiting_key] = True
                    st.rerun()

            if live_completed.strip():
                st.code(live_completed.rstrip("\n"), language="text")
            elif not live_running and not str(st.session_state.get(prompt_key, "")).strip():
                st.code("（尚未啟動）", language="text")

        _live_output()

        live_session = get_terminal_session(session_key)
        if live_session is not None and is_running(live_session) and display_prompt.strip():
            _render_prompt_input_inline(
                session_key=session_key,
                session=live_session,
                prompt=display_prompt,
                disabled=disabled,
            )


def render_agent_terminal(
    *,
    session_key: str,
    agent_py: Path,
    google_sub: str,
    disabled: bool = False,
    start_button_label: str = "▶ 啟動 Agent",
    stop_button_label: str = "⏹ 結束 Agent（Ctrl+C）",
    title: str = "Agent 終端機",
    caption_text: str = "啟動後一行一行輸入；`bye` 優雅離開，或 ⏹ 等同 Ctrl+C 強制結束。",
    input_mode: InputMode = "button",
    show_turn_count: bool = True,
    layout: LayoutMode = "split",
) -> AgentTerminalSession | None:
    st.markdown(f"**{title}**")
    st.caption(caption_text)

    if layout == "inline":
        st.markdown(_INLINE_TERMINAL_CSS, unsafe_allow_html=True)

    session = get_terminal_session(session_key)
    _refresh_terminal_output(session_key, session)

    if layout == "inline":
        session = _render_terminal_controls(
            session_key=session_key,
            session=session,
            agent_py=agent_py,
            google_sub=google_sub,
            disabled=disabled,
            start_button_label=start_button_label,
            stop_button_label=stop_button_label,
        )
        _render_inline_terminal_panel(session_key=session_key, disabled=disabled)

        session = get_terminal_session(session_key)
        if session is not None and session.state == TerminalState.EXITED:
            st.caption(f"Agent 已結束（exit={session.exit_code}）")
        elif session is not None and is_running(session):
            st.caption("執行中 · prompt 後輸入，Enter 送出")
        return session

    output = str(st.session_state.get(_session_state_key(_OUTPUT_KEY, session_key), ""))
    st.code(output or "（尚未啟動）", language="text")

    if session is not None and session.state == TerminalState.EXITED:
        st.caption(f"Agent 已結束（turns={session.turn_count}，exit={session.exit_code}）")
    elif session is not None and is_running(session):
        if show_turn_count:
            st.caption(f"執行中 · 已對話 {session.turn_count} 輪（不含 bye）")
        else:
            st.caption("執行中")

    ctrl = st.columns([2, 2, 3])
    with ctrl[0]:
        if st.button(
            start_button_label,
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
            stop_button_label,
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
        _render_split_input_area(
            session_key=session_key,
            session=session,
            disabled=disabled,
            input_mode=input_mode,
        )

    return get_terminal_session(session_key)


_FORGE_INLINE_CAPTION = "按執行後，在執行結果框內 prompt 後輸入；Enter 送出。⏹ 可強制結束。"


def render_forge_inline_terminal(
    *,
    session_key: str,
    agent_py: Path,
    google_sub: str,
    disabled: bool = False,
) -> AgentTerminalSession | None:
    """Forge Skill Forge / Lab 共用 inline terminal（與 Brain C1 同款）。"""
    return render_agent_terminal(
        session_key=session_key,
        agent_py=agent_py,
        google_sub=google_sub,
        disabled=disabled,
        start_button_label="▶ 執行",
        stop_button_label="⏹ 結束",
        title="執行結果",
        caption_text=_FORGE_INLINE_CAPTION,
        input_mode="form",
        show_turn_count=False,
        layout="inline",
    )
