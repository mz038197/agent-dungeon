from __future__ import annotations

from agent_dungeon.forge.forge_terminal_ui import (
    poll_interval_for_terminal,
    should_exit_processing,
)


def test_should_exit_processing_when_not_running() -> None:
    assert should_exit_processing("hello\n", 0, running=False) is True


def test_should_exit_processing_waits_for_newline_after_snapshot() -> None:
    stdout = "你的問題: hi"
    assert should_exit_processing(stdout, len(stdout), running=True) is False
    stdout = "你的問題: hi\nBrain 回覆\n"
    assert should_exit_processing(stdout, len("你的問題: hi"), running=True) is True


def test_poll_interval_processing_keeps_polling() -> None:
    assert poll_interval_for_terminal(processing=True, awaiting_input=False, running=True) == 0.2


def test_poll_interval_awaiting_input_pauses() -> None:
    assert poll_interval_for_terminal(processing=False, awaiting_input=True, running=True) is None


def test_poll_interval_running_without_awaiting_polls() -> None:
    assert poll_interval_for_terminal(processing=False, awaiting_input=False, running=True) == 0.2
