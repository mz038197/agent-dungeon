from __future__ import annotations

from agent_dungeon.forge.forge_terminal_css import inline_terminal_css_block
from agent_dungeon.forge.forge_terminal_ui import (
    _FORGE_INLINE_CAPTION,
    render_forge_inline_terminal,
    render_agent_terminal,
)


def test_render_forge_inline_terminal_delegates_to_inline_layout(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_render_agent_terminal(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(
        "agent_dungeon.forge.forge_terminal_ui.render_agent_terminal",
        _fake_render_agent_terminal,
    )

    render_forge_inline_terminal(
        session_key="brain_forge_c1_terminal",
        agent_py=__file__,
        google_sub="sub-a",
        disabled=True,
    )

    assert captured["layout"] == "inline"
    assert captured["input_mode"] == "form"
    assert captured["show_turn_count"] is False
    assert captured["caption_text"] == _FORGE_INLINE_CAPTION
    assert captured["start_button_label"] == "▶ 執行"
    assert captured["disabled"] is True


def test_forge_inline_caption_is_stable() -> None:
    assert "Enter" in _FORGE_INLINE_CAPTION
    assert render_agent_terminal is not None


def test_inline_terminal_css_uses_direct_child_block_selector() -> None:
    css = inline_terminal_css_block()
    assert ':has(> [data-testid="stElementContainer"]:has([data-forge-terminal' in css
    assert ':has([data-forge-terminal' in css
    broad_block = (
        '> [data-testid="stVerticalBlock"]:has([data-forge-terminal'
    )
    assert broad_block not in css
