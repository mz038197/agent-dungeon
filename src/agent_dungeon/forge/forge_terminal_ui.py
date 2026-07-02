from __future__ import annotations

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
from agent_dungeon.forge.forge_terminal_css import inline_terminal_css_block
from agent_dungeon.forge.forge_terminal_html import (
    normalize_inline_terminal_stdout,
    split_stdout_pending_prompt,
)
from agent_dungeon.ui.shell_ui import inject_css_block

_SESSION_KEY = "forge_terminal_session"
_OUTPUT_KEY = "forge_terminal_output"

InputMode = Literal["button", "form"]
LayoutMode = Literal["split", "inline"]

_PROMPT_KEY = "forge_terminal_pending_prompt"
_AWAITING_KEY = "forge_terminal_awaiting_input"
_PROCESSING_KEY = "forge_terminal_processing"
_OUTPUT_SNAPSHOT_KEY = "forge_terminal_output_snapshot"
_PROCESSING_PROMPT_KEY = "forge_terminal_processing_prompt"
_WAS_RUNNING_KEY = "forge_terminal_was_running"
_LAST_SUBMIT_KEY = "forge_terminal_last_submit"

_PROCESSING_PLACEHOLDER = "Brain 思考中…"


def _session_state_key(base: str, session_key: str) -> str:
    return f"{session_key}_{base}"


def should_exit_processing(stdout: str, snapshot_len: int, *, running: bool) -> bool:
    """送出 input 後，snapshot 之後出現換行或 process 結束即離開 processing。"""
    if not running:
        return True
    if snapshot_len < 0:
        return False
    if len(stdout) <= snapshot_len:
        return False
    return "\n" in stdout[snapshot_len:]


def poll_interval_for_terminal(
    *,
    processing: bool,
    awaiting_input: bool,
    running: bool,
) -> float | None:
    del processing, awaiting_input
    if running:
        return 0.2
    return None


def should_handle_natural_exit(*, was_running: bool, live_running: bool) -> bool:
    """程序自然結束（was_running 且本輪已不在跑）時應清理並刷新 UI。"""
    return was_running and not live_running


def should_rerun_on_natural_exit(*, was_running: bool, live_running: bool) -> bool:
    """程序自然結束（was_running 且本輪已不在跑）時應 rerun 刷新外層 UI。"""
    return should_handle_natural_exit(was_running=was_running, live_running=live_running)


def _clear_inline_terminal_input_state(session_key: str) -> None:
    st.session_state[_session_state_key(_AWAITING_KEY, session_key)] = False
    st.session_state[_session_state_key(_PROMPT_KEY, session_key)] = ""
    st.session_state[_session_state_key(_PROCESSING_KEY, session_key)] = False
    st.session_state.pop(_session_state_key(_OUTPUT_SNAPSHOT_KEY, session_key), None)
    st.session_state.pop(_session_state_key(_PROCESSING_PROMPT_KEY, session_key), None)
    st.session_state.pop(_session_state_key(_LAST_SUBMIT_KEY, session_key), None)


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
    st.session_state.pop(_session_state_key(_PROCESSING_KEY, session_key), None)
    st.session_state.pop(_session_state_key(_OUTPUT_SNAPSHOT_KEY, session_key), None)
    st.session_state.pop(_session_state_key(_PROCESSING_PROMPT_KEY, session_key), None)
    st.session_state.pop(_session_state_key(_WAS_RUNNING_KEY, session_key), None)
    st.session_state.pop(_session_state_key(_LAST_SUBMIT_KEY, session_key), None)


def _refresh_terminal_output(session_key: str, session: AgentTerminalSession | None) -> str:
    if session is not None:
        poll_output(session)
        st.session_state[_session_state_key(_OUTPUT_KEY, session_key)] = session.effective_output()
    return str(st.session_state.get(_session_state_key(_OUTPUT_KEY, session_key), ""))


def _processing_prompt_and_input(
    session: AgentTerminalSession | None,
    session_key: str,
) -> tuple[str, str]:
    processing_prompt_key = _session_state_key(_PROCESSING_PROMPT_KEY, session_key)
    last_submit_key = _session_state_key(_LAST_SUBMIT_KEY, session_key)
    prompt = str(st.session_state.get(processing_prompt_key, ""))
    last_input = session.input_lines[-1] if session and session.input_lines else ""
    last_submit = st.session_state.get(last_submit_key)
    if isinstance(last_submit, dict):
        if not prompt:
            prompt = str(last_submit.get("prompt", ""))
        if not last_input:
            last_input = str(last_submit.get("input", ""))
    return prompt, last_input


def unified_terminal_display_text(
    stdout: str,
    *,
    session: AgentTerminalSession | None,
    session_key: str,
    processing: bool,
    live_running: bool,
) -> str:
    """單一 inline terminal 輸出區的顯示文字。"""
    if not live_running:
        completed = split_stdout_pending_prompt(stdout, awaiting_input=False)[0]
        return completed.rstrip("\n") if completed.strip() else ""

    if processing:
        prompt, last_input = _processing_prompt_and_input(session, session_key)
        normalized = normalize_inline_terminal_stdout(
            stdout,
            prompt=prompt,
            last_input=last_input,
        )
        if last_input:
            submitted = f"{prompt}{last_input}"
            submitted_alt = f"{prompt.rstrip()}{last_input}"
            if submitted not in normalized and submitted_alt not in normalized:
                trimmed = normalized.rstrip()
                if trimmed.endswith(prompt.rstrip()) or trimmed.endswith(prompt):
                    normalized = f"{trimmed}{last_input}"
        return normalized.rstrip("\n")

    return stdout.rstrip("\n")


def should_show_inline_terminal_panel(
    *,
    output: str,
    running: bool,
    processing: bool,
) -> bool:
    """Forge inline terminal：按執行後或已有 stdout 才顯示輸出區。"""
    return running or processing or bool(output.strip())


def _render_unified_terminal_output(display: str, *, placeholder: str = "（尚未啟動）") -> None:
    st.code(display.rstrip("\n") if display.strip() else placeholder, language="text")


def _submit_terminal_input(
    session: AgentTerminalSession,
    *,
    session_key: str,
    line: str,
) -> None:
    prompt_key = _session_state_key(_PROMPT_KEY, session_key)
    processing_prompt_key = _session_state_key(_PROCESSING_PROMPT_KEY, session_key)
    last_submit_key = _session_state_key(_LAST_SUBMIT_KEY, session_key)
    st.session_state[processing_prompt_key] = str(st.session_state.get(prompt_key, ""))
    st.session_state[last_submit_key] = {
        "prompt": str(st.session_state.get(prompt_key, "")),
        "input": line.strip(),
    }
    send_input(session, line)
    st.session_state[_session_state_key(_AWAITING_KEY, session_key)] = False
    st.session_state[prompt_key] = ""
    st.session_state[_session_state_key(_PROCESSING_KEY, session_key)] = True
    st.session_state[_session_state_key(_OUTPUT_SNAPSHOT_KEY, session_key)] = len(
        session.stdout_buffer
    )
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
            st.session_state[_session_state_key(_WAS_RUNNING_KEY, session_key)] = True
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
    disabled: bool,
    placeholder: str = "在此輸入…",
) -> None:
    input_disabled = disabled or not is_running(session)

    st.markdown(
        '<span data-forge-terminal-input="inline" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    with st.form(key=f"{session_key}_inline_form", clear_on_submit=True, border=False):
        input_col, btn_col = st.columns([5, 1], gap="small", vertical_alignment="bottom")
        with input_col:
            line = st.text_input(
                "輸入",
                key=f"{session_key}_input_line",
                disabled=input_disabled,
                placeholder=placeholder,
                label_visibility="collapsed",
            )
        with btn_col:
            submitted = st.form_submit_button(
                "送出",
                disabled=input_disabled,
                use_container_width=True,
            )

    if submitted and str(line).strip() and not input_disabled:
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

    awaiting_key = _session_state_key(_AWAITING_KEY, session_key)
    prompt_key = _session_state_key(_PROMPT_KEY, session_key)
    processing_key = _session_state_key(_PROCESSING_KEY, session_key)
    snapshot_key = _session_state_key(_OUTPUT_SNAPSHOT_KEY, session_key)
    processing_prompt_key = _session_state_key(_PROCESSING_PROMPT_KEY, session_key)
    was_running_key = _session_state_key(_WAS_RUNNING_KEY, session_key)

    if not running:
        st.session_state[awaiting_key] = False
        st.session_state[prompt_key] = ""
        st.session_state[processing_key] = False

    if should_handle_natural_exit(
        was_running=bool(st.session_state.get(was_running_key, False)),
        live_running=running,
    ):
        _clear_inline_terminal_input_state(session_key)
        st.session_state[was_running_key] = False
        st.rerun()

    processing = bool(st.session_state.get(processing_key, False))
    if processing:
        snapshot_len = int(st.session_state.get(snapshot_key, 0))
        if should_exit_processing(output, snapshot_len, running=running):
            st.session_state[processing_key] = False
            st.session_state.pop(processing_prompt_key, None)
            processing = False

    split_awaiting = running and not processing
    completed, prompt = split_stdout_pending_prompt(output, awaiting_input=split_awaiting)

    if running and prompt.strip() and not processing:
        st.session_state[prompt_key] = prompt
        if not st.session_state.get(awaiting_key):
            st.session_state[awaiting_key] = True
            st.rerun()
    elif running and not prompt.strip() and not processing:
        st.session_state[awaiting_key] = False

    awaiting_input = bool(
        running and not processing and st.session_state.get(awaiting_key) and prompt.strip()
    )
    poll_interval = poll_interval_for_terminal(
        processing=processing,
        awaiting_input=awaiting_input,
        running=running,
    )
    display_prompt = str(st.session_state.get(prompt_key, ""))
    if processing:
        display_prompt = str(st.session_state.get(processing_prompt_key, display_prompt))

    if not should_show_inline_terminal_panel(
        output=output,
        running=running,
        processing=processing,
    ):
        return

    with st.container(border=True):
        st.markdown(
            '<div data-forge-terminal="inline" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )
        output_slot = st.empty()

        @st.fragment(run_every=poll_interval)
        def _live_output() -> None:
            live_session = get_terminal_session(session_key)
            live_output = _refresh_terminal_output(session_key, live_session)
            live_running = live_session is not None and is_running(live_session)
            live_processing = bool(st.session_state.get(processing_key, False))
            if live_processing and live_session is not None:
                live_snapshot = int(st.session_state.get(snapshot_key, 0))
                if should_exit_processing(
                    live_output,
                    live_snapshot,
                    running=live_running,
                ):
                    st.session_state[processing_key] = False
                    st.session_state.pop(processing_prompt_key, None)
                    live_processing = False

            live_split_awaiting = live_running and not live_processing
            _, live_prompt = split_stdout_pending_prompt(
                live_output,
                awaiting_input=live_split_awaiting,
            )

            if live_running and live_prompt.strip() and not live_processing:
                st.session_state[prompt_key] = live_prompt
                if not st.session_state.get(awaiting_key):
                    st.session_state[awaiting_key] = True
                    st.rerun()

            if live_running:
                st.session_state[was_running_key] = True
            elif should_rerun_on_natural_exit(
                was_running=bool(st.session_state.get(was_running_key, False)),
                live_running=live_running,
            ):
                _clear_inline_terminal_input_state(session_key)
                st.session_state[was_running_key] = False
                st.rerun()

            display = unified_terminal_display_text(
                live_output,
                session=live_session,
                session_key=session_key,
                processing=live_processing,
                live_running=live_running,
            )
            with output_slot.container():
                if display.strip():
                    _render_unified_terminal_output(display)
                else:
                    output_slot.empty()

        _live_output()

        live_session = get_terminal_session(session_key)
        live_processing = bool(st.session_state.get(processing_key, False))
        show_input = live_session is not None and is_running(live_session) and (
            live_processing or display_prompt.strip()
        )
        if show_input:
            _render_prompt_input_inline(
                session_key=session_key,
                session=live_session,
                disabled=disabled or live_processing,
                placeholder=_PROCESSING_PLACEHOLDER if live_processing else "在此輸入…",
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
        inject_css_block(inline_terminal_css_block(), element_id="forge-terminal-inline-css")

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
            if st.session_state.get(_session_state_key(_PROCESSING_KEY, session_key), False):
                st.caption("執行中 · Brain 思考中…")
            else:
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
            st.session_state[_session_state_key(_WAS_RUNNING_KEY, session_key)] = True
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
