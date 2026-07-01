from __future__ import annotations

from pathlib import Path

import pytest

from agent_dungeon.core.progress import DungeonProgress
from agent_dungeon.forge.agent_py_store import (
    agent_py_path,
    build_agent_py_from_main,
    extract_agent_main_source,
    read_agent_py,
    sync_voice_forge_challenge_to_agent_py,
)
from agent_dungeon.forge.challenges import voice_forge_lab_seed_code


def test_voice_forge_lab_seed_from_c3() -> None:
    c3 = """def main():
    print("Hello")

if __name__ == "__main__":
    main()
"""
    seed = voice_forge_lab_seed_code({"c3": c3})
    assert 'print("Hello")' in seed
    assert "再加一句自我介紹" in seed
    assert "# Code Here #" in seed
    assert "# main()" not in seed
    assert 'print("Hi there!")' not in seed


def test_sync_voice_forge_writes_c1_to_agent_py(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    google_sub = "test-voice-sync"
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

    sync_voice_forge_challenge_to_agent_py(
        google_sub,
        'print("Hello")',
        progress=progress,
    )
    path = agent_py_path(google_sub)
    source = read_agent_py(path)
    main = extract_agent_main_source(source)
    assert 'print("Hello")' in main
    assert source.count('if __name__ == "__main__":') == 1


def test_voice_lab_code_not_used_for_agent_py_main() -> None:
    c3 = """def main():
    print("Hello")

if __name__ == "__main__":
    main()
"""
    lab = """def main():
    print("Hello")
    print("Practice line two.")

if __name__ == "__main__":
    main()
"""
    c3_main = extract_agent_main_source(build_agent_py_from_main(c3))
    lab_main = extract_agent_main_source(build_agent_py_from_main(lab))
    assert "Practice line two." not in c3_main
    assert 'print("Hello")' in c3_main
    assert "Practice line two." in lab_main
