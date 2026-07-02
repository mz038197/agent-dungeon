from __future__ import annotations

from pathlib import Path

import pytest

from agent_dungeon.agent.agent_py_preview import build_agent_py_preview
from agent_dungeon.core.progress import DungeonProgress
from agent_dungeon.forge.agent_py_store import (
    build_agent_py_template,
    extract_agent_main_source,
    read_agent_py,
    sync_voice_forge_challenge_to_agent_py,
    write_agent_py,
)


def test_preview_reads_agent_py_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    agent_file = tmp_path / "agent.py"
    content = build_agent_py_template(progress=DungeonProgress())
    write_agent_py(agent_file, content)

    preview = build_agent_py_preview(DungeonProgress(), agent_py_path=str(agent_file))
    assert 'def main():' in preview
    assert 'if __name__ == "__main__":' in preview
    assert "Agent Dungeon" in preview


def test_preview_fallback_template_without_path() -> None:
    preview = build_agent_py_preview(DungeonProgress())
    assert "def main():" in preview
    assert "Agent Dungeon" in preview


def test_sync_strips_comments_from_disk(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    google_sub = "test-sync-strip"
    progress = DungeonProgress()

    def fake_paths_for_user(sub: str):
        from agent_dungeon.core.cloud_paths import UserPaths

        root = tmp_path / sub
        workspace = root / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        return UserPaths(
            google_sub=sub,
            root=root,
            profile=root / "profile.json",
            progress=root / "progress.json",
            workspace=workspace,
            agent_py=workspace / "agent.py",
            sessions=workspace / "sessions",
            page_data=root / "page_data",
            chat_images=workspace / "uploads" / "chat_images",
            tts=root / "tts.json",
            preferences=root / "preferences.json",
            effective_config=root / "effective_config.json",
        )

    monkeypatch.setattr(
        "agent_dungeon.forge.agent_py_store.paths_for_user",
        fake_paths_for_user,
    )

    editor = """def main():
    # TODO: 用 input() 取得 question，再用 print 顯示
    # Code Here #
    print("Hello")
"""
    sync_voice_forge_challenge_to_agent_py(google_sub, editor, progress=progress)
    from agent_dungeon.forge.agent_py_store import agent_py_path

    path = agent_py_path(google_sub)
    main = extract_agent_main_source(read_agent_py(path))
    assert "TODO" not in main
    assert "Code Here" not in main
    assert 'print("Hello")' in main
