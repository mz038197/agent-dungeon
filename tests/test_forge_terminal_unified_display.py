from __future__ import annotations

from agent_dungeon.forge.forge_terminal_ui import unified_terminal_display_text


def test_unified_display_awaiting_shows_full_stdout() -> None:
    raw = "LLM reply\n你的問題："
    out = unified_terminal_display_text(
        raw,
        session=None,
        session_key="test",
        processing=False,
        live_running=True,
    )
    assert out == raw


def test_unified_display_exited_uses_full_completed_buffer() -> None:
    raw = "Hello\n你的問題： "
    out = unified_terminal_display_text(
        raw,
        session=None,
        session_key="test",
        processing=False,
        live_running=False,
    )
    assert out == raw.rstrip("\n")


def test_unified_display_exited_empty() -> None:
    out = unified_terminal_display_text(
        "",
        session=None,
        session_key="test",
        processing=False,
        live_running=False,
    )
    assert out == ""


def test_unified_display_processing_appends_input_when_stdout_only_has_prompt(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "agent_dungeon.forge.forge_terminal_ui.st.session_state",
        {
            "test_forge_terminal_processing_prompt": "你的問題：",
            "test_forge_terminal_last_submit": {"prompt": "你的問題：", "input": "你好"},
        },
    )
    out = unified_terminal_display_text(
        "你的問題：",
        session=None,
        session_key="test",
        processing=True,
        live_running=True,
    )
    assert out == "你的問題：你好"


def test_unified_display_processing_does_not_duplicate_input(monkeypatch) -> None:
    monkeypatch.setattr(
        "agent_dungeon.forge.forge_terminal_ui.st.session_state",
        {
            "test_forge_terminal_processing_prompt": "你的問題：",
            "test_forge_terminal_last_submit": {"prompt": "你的問題：", "input": "你好"},
        },
    )
    raw = "你的問題：你好"
    out = unified_terminal_display_text(
        raw,
        session=None,
        session_key="test",
        processing=True,
        live_running=True,
    )
    assert out == raw
