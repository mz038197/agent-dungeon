from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def test_voice_page_includes_login_bootstrap() -> None:
    voice_path = Path(__file__).resolve().parent.parent / "pages" / "0_Voice.py"
    source = voice_path.read_text(encoding="utf-8")
    assert "init_dungeon_environment()" in source
    assert "require_dungeon_login()" in source
    assert source.index("init_dungeon_environment()") < source.index("st.set_page_config")
    assert source.index("st.set_page_config") < source.index("require_dungeon_login()")


def test_page_bootstrap_module_loads() -> None:
    root = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location("page_bootstrap", root / "page_bootstrap.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert callable(module.init_dungeon_environment)
    assert callable(module.require_dungeon_login)
