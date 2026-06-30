from __future__ import annotations

from pathlib import Path

from agent_dungeon.ui.shell_ui import _MULTIMODAL_CHATINPUT_LIGHT_CSS, multimodal_chatinput_light_theme_js


def test_multimodal_patch_includes_inner_observer_and_color_scheme() -> None:
    js = multimodal_chatinput_light_theme_js()
    assert "installInnerObserver" in js
    assert "ensureChatinputLightTheme" in js
    assert "dungeonChatinputLoadBound" in js
    assert "__dungeonMultimodalChatinputHostObserver" in js
    assert "color-scheme: light" in _MULTIMODAL_CHATINPUT_LIGHT_CSS


def test_dungeon_shell_css_distinguishes_primary_and_secondary_buttons() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    pkg_root = repo_root / "src" / "agent_dungeon"
    css = (pkg_root / "ui" / "dungeon_shell.py").read_text(
        encoding="utf-8"
    )
    assert 'button[data-testid="stBaseButton-primary"]' in css
    assert "background-color: #6366f1 !important" in css
    assert "background-color: #4f46e5 !important" in css
    assert '[data-testid="stButton"] button,' not in css.split("次要按鈕")[1].split("primary")[0]
    assert "stPageLink" in css
    assert "disableComponentPointerCapture" in (
        pkg_root / "ui" / "shell_ui.py"
    ).read_text(encoding="utf-8")


def test_streamlit_config_forces_light_theme() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    pkg_root = repo_root / "src" / "agent_dungeon"
    config = (
        pkg_root / ".streamlit" / "config.toml"
    ).read_text(encoding="utf-8")
    assert 'base = "light"' in config
    assert 'primaryColor = "#6366f1"' in config


def test_shell_flush_css_covers_top_and_bottom() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    shell_ui = (repo_root / "src" / "agent_dungeon" / "ui" / "shell_ui.py").read_text(
        encoding="utf-8"
    )
    dungeon_shell = (
        repo_root / "src" / "agent_dungeon" / "ui" / "dungeon_shell.py"
    ).read_text(encoding="utf-8")
    assert "padding-bottom: 0 !important" in shell_ui
    assert "#dungeon-css-anchor" in shell_ui
    assert "#dungeon-paint-anchor" in shell_ui
    assert "dungeon-shell-flush-bottom" in shell_ui
    assert "flushShellToBottom" in dungeon_shell
    assert "margin-top: 0 !important" in dungeon_shell.split("Footer 深藍底")[1]
    assert "border-radius: 0 !important" in dungeon_shell.split("Footer 深藍底")[1]
    assert "stVerticalBlock" in dungeon_shell
    assert "dungeon-post-complete-band" in dungeon_shell


def test_skill_forge_hint_styles_and_no_caption() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    pkg_root = repo_root / "src" / "agent_dungeon"
    dungeon_shell = (pkg_root / "ui" / "dungeon_shell.py").read_text(encoding="utf-8")
    skill_forge_ui = (pkg_root / "forge" / "skill_forge_ui.py").read_text(encoding="utf-8")
    shell_ui = (pkg_root / "ui" / "shell_ui.py").read_text(encoding="utf-8")

    from agent_dungeon.forge.challenges import BRAIN_FORGE_CHALLENGES, VOICE_FORGE_CHALLENGES

    assert "skill-forge-summary" in dungeon_shell
    assert "skill-forge-editor-hint" in dungeon_shell
    assert "skill-forge-note" in dungeon_shell
    assert "color: #334155" in dungeon_shell.split("skill-forge-editor-hint")[1]
    assert "render_skill_forge_summary" in shell_ui
    assert "render_editor_hint" in shell_ui
    assert "render_skill_forge_note" in shell_ui
    assert "st.caption" not in skill_forge_ui
    assert "render_skill_forge_summary" in skill_forge_ui
    assert "render_editor_hint" in skill_forge_ui
    assert "render_skill_forge_note" in skill_forge_ui

    for challenges in (VOICE_FORGE_CHALLENGES, BRAIN_FORGE_CHALLENGES):
        assert len(challenges) == 3
        assert all(challenge.editor_hint.strip() for challenge in challenges)
