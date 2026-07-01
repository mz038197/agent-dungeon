from __future__ import annotations

import io
import json
import zipfile

import pytest

from agent_dungeon.core.progress import DungeonProgress, ModuleStatus, is_dungeon_graduated
from agent_dungeon.forge.agent_py_store import build_agent_py_template
from agent_dungeon.forge.forge_runtime.registry import (
    build_export_header,
    build_platform_header,
    export_runtime_modules,
    rewrite_agent_py_header,
)
from agent_dungeon.forge.graduation_export import build_graduation_zip, graduation_zip_filename


def _graduated_progress() -> DungeonProgress:
    progress = DungeonProgress()
    for module_id in progress.modules:
        progress.modules[module_id] = ModuleStatus.COMPLETE
    return progress


def test_is_dungeon_graduated_requires_all_modules() -> None:
    progress = DungeonProgress()
    assert is_dungeon_graduated(progress) is False
    progress.modules["voice"] = ModuleStatus.COMPLETE
    assert is_dungeon_graduated(progress) is False
    assert is_dungeon_graduated(_graduated_progress()) is True


def test_platform_header_contains_brain_binding() -> None:
    header = build_platform_header()
    assert "get_brain_class" in header
    assert "Brain = get_brain_class" in header


def test_export_header_uses_runtime_import() -> None:
    progress = _graduated_progress()
    header = build_export_header(progress=progress)
    assert header.endswith("from runtime import Brain")


def test_rewrite_agent_py_header() -> None:
    progress = _graduated_progress()
    source = build_agent_py_template(progress=progress)
    rewritten = rewrite_agent_py_header(source, progress=progress)
    assert rewritten.startswith('"""Agent Dungeon — 你的 Agent（agent.py）"""\nfrom runtime import Brain')
    assert "agent_dungeon.forge.agent_runtime" not in rewritten
    assert "def main():" in rewritten
    assert "# === Voice 模組 ===" not in rewritten


def test_export_runtime_modules_includes_brain() -> None:
    files = export_runtime_modules(progress=_graduated_progress())
    assert "runtime/brain.py" in files
    assert "runtime/__init__.py" in files
    assert "class Brain:" in files["runtime/brain.py"]
    assert "use_responses_api" in files["runtime/brain.py"]


def test_build_graduation_zip_requires_graduation(tmp_path, monkeypatch) -> None:
    progress = DungeonProgress()
    with pytest.raises(ValueError, match="八關全通"):
        build_graduation_zip(
            google_sub="sub-a",
            progress=progress,
            display_name="Ada",
        )


def test_build_graduation_zip_contents(tmp_path, monkeypatch) -> None:
    from agent_dungeon.forge import agent_py_store, graduation_export

    progress = _graduated_progress()
    agent_path = tmp_path / "agent.py"
    agent_path.write_text(build_agent_py_template(progress=progress), encoding="utf-8")
    monkeypatch.setattr(graduation_export, "agent_py_path", lambda _sub: agent_path)
    monkeypatch.setattr(agent_py_store, "agent_py_path", lambda _sub: agent_path)

    payload = build_graduation_zip(
        google_sub="sub-a",
        progress=progress,
        display_name="Ada Lovelace",
    )
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = set(archive.namelist())
        assert "agent.py" in names
        assert "runtime/brain.py" in names
        assert "manifest.json" in names
        agent_source = archive.read("agent.py").decode("utf-8")
        assert "from runtime import Brain" in agent_source
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        assert manifest["install_mode"] == "in_place"
        assert manifest["entrypoint"] == "agent.py"


def test_graduation_zip_filename_sanitizes_display_name() -> None:
    assert graduation_zip_filename(display_name="Ada Lovelace", google_sub="sub") == "Ada-Lovelace-agent.zip"
