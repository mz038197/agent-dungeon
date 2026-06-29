from __future__ import annotations

from pathlib import Path

from shell_ui import _MULTIMODAL_CHATINPUT_LIGHT_CSS, multimodal_chatinput_light_theme_js


def test_multimodal_patch_includes_inner_observer_and_color_scheme() -> None:
    js = multimodal_chatinput_light_theme_js()
    assert "installInnerObserver" in js
    assert "ensureChatinputLightTheme" in js
    assert "dungeonChatinputLoadBound" in js
    assert "__dungeonMultimodalChatinputHostObserver" in js
    assert "color-scheme: light" in _MULTIMODAL_CHATINPUT_LIGHT_CSS


def test_dungeon_shell_css_distinguishes_primary_and_secondary_buttons() -> None:
    css = (Path(__file__).resolve().parent.parent / "dungeon_shell.py").read_text(
        encoding="utf-8"
    )
    assert 'button[data-testid="stBaseButton-primary"]' in css
    assert "background-color: #6366f1 !important" in css
    assert "background-color: #4f46e5 !important" in css
    assert '[data-testid="stButton"] button,' not in css.split("次要按鈕")[1].split("primary")[0]
    assert "stPageLink" in css
    assert "disableComponentPointerCapture" in (
        Path(__file__).resolve().parent.parent / "shell_ui.py"
    ).read_text(encoding="utf-8")


def test_streamlit_config_forces_light_theme() -> None:
    config = (
        Path(__file__).resolve().parent.parent / ".streamlit" / "config.toml"
    ).read_text(encoding="utf-8")
    assert 'base = "light"' in config
    assert 'primaryColor = "#6366f1"' in config
