from __future__ import annotations

from agent_dungeon.forge.forge_terminal_html import (
    build_terminal_srcdoc,
    split_stdout_pending_prompt,
    terminal_iframe_height,
)


def test_split_stdout_pending_prompt_with_trailing_prompt() -> None:
    completed, prompt = split_stdout_pending_prompt("Hello\n你想問什麼？ ", awaiting_input=True)
    assert completed == "Hello\n"
    assert prompt == "你想問什麼？ "


def test_split_stdout_no_pending_when_awaiting_false() -> None:
    completed, prompt = split_stdout_pending_prompt("Hello\n你想問什麼？ ", awaiting_input=False)
    assert completed == "Hello\n你想問什麼？ "
    assert prompt == ""


def test_split_stdout_only_prompt() -> None:
    completed, prompt = split_stdout_pending_prompt("你想問什麼？ ", awaiting_input=True)
    assert completed == ""
    assert prompt == "你想問什麼？ "


def test_build_terminal_srcdoc_contains_prompt_and_session() -> None:
    doc = build_terminal_srcdoc(
        completed="Hello\n",
        prompt="你想問什麼？ ",
        editable=True,
        session_key="brain_forge_c1_terminal",
    )
    assert "forge_terminal_input" in doc
    assert "brain_forge_c1_terminal" in doc
    assert "Hello" in doc


def test_terminal_iframe_height_scales() -> None:
    assert terminal_iframe_height("", has_prompt=False) >= 160
    tall = terminal_iframe_height("\n".join(f"line{i}" for i in range(20)), has_prompt=True)
    assert tall <= 320
