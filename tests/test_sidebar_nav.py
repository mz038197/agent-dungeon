from __future__ import annotations

from pathlib import Path

from agent_dungeon.core.progress import ModuleStatus
from agent_dungeon.ui.shell_ui import discover_file_pages, navigation_page_path, page_url_from_relative_page
from agent_dungeon.ui.sidebar_nav import _status_label, _status_pill_class


def test_status_label_for_each_module_status() -> None:
    assert _status_label(ModuleStatus.IN_PROGRESS) == "進行中"
    assert _status_label(ModuleStatus.COMPLETE) == "已完成"
    assert _status_label(ModuleStatus.LOCKED) == "未解鎖"


def test_status_pill_class_for_each_module_status() -> None:
    assert _status_pill_class(ModuleStatus.IN_PROGRESS) == "in-progress"
    assert _status_pill_class(ModuleStatus.COMPLETE) == "complete"
    assert _status_pill_class(ModuleStatus.LOCKED) == "locked"


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
    loop = next(path for path in pages if path.name == "2_Loop.py")
    assert navigation_page_path(loop.relative_to(app_root).as_posix()) == "level_pages/2_Loop.py"


def test_sidebar_nav_uses_page_link_not_raw_href() -> None:
    source = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "agent_dungeon"
        / "ui"
        / "sidebar_nav.py"
    ).read_text(encoding="utf-8")
    assert "st.page_link" in source
    assert "dungeon-module-name-link" not in source
    assert "page_url_from_relative_page" not in source
