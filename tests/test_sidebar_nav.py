from __future__ import annotations

from pathlib import Path

from agent_dungeon.ui.shell_ui import discover_file_pages, navigation_page_path, page_url_from_relative_page


def test_navigation_page_path_uses_posix_slashes() -> None:
    assert navigation_page_path("level_pages\\0_Voice.py") == "level_pages/0_Voice.py"


def test_page_url_from_relative_page_uses_streamlit_title_url() -> None:
    assert page_url_from_relative_page("level_pages/0_Voice.py") == "/Voice"


def test_discover_file_pages_includes_voice_with_relative_ref() -> None:
    app_root = Path(__file__).resolve().parent.parent / "src" / "agent_dungeon"
    pages = list(discover_file_pages(app_root / "level_pages"))
    voice = next(path for path in pages if path.name == "0_Voice.py")
    assert navigation_page_path(voice.relative_to(app_root).as_posix()) == "level_pages/0_Voice.py"
    brain = next(path for path in pages if path.name == "1_Brain.py")
    assert navigation_page_path(brain.relative_to(app_root).as_posix()) == "level_pages/1_Brain.py"
