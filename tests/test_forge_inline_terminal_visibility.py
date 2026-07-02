from __future__ import annotations

from agent_dungeon.forge.forge_terminal_ui import should_show_inline_terminal_panel


def test_should_show_inline_terminal_panel_idle() -> None:
    assert (
        should_show_inline_terminal_panel(
            output="",
            running=False,
            processing=False,
        )
        is False
    )


def test_should_show_inline_terminal_panel_when_running() -> None:
    assert (
        should_show_inline_terminal_panel(
            output="",
            running=True,
            processing=False,
        )
        is True
    )


def test_should_show_inline_terminal_panel_when_processing() -> None:
    assert (
        should_show_inline_terminal_panel(
            output="",
            running=False,
            processing=True,
        )
        is True
    )


def test_should_show_inline_terminal_panel_after_output() -> None:
    assert (
        should_show_inline_terminal_panel(
            output="Hello\n",
            running=False,
            processing=False,
        )
        is True
    )
