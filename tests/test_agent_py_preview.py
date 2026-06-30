from __future__ import annotations

from agent_dungeon.agent.agent_py_preview import build_agent_py_preview
from agent_dungeon.core.progress import (
    DungeonProgress,
    mark_forge_challenge_complete,
    mark_forge_lab_complete,
)


def test_preview_locked_before_forge() -> None:
    preview = build_agent_py_preview(DungeonProgress())
    assert "# agent.py — 建造中" in preview
    assert "# 🔒 完成 Skill Forge 解鎖" in preview
    assert "# 🔒 尚未解鎖" in preview


def test_preview_grows_with_c1() -> None:
    progress = DungeonProgress()
    mark_forge_challenge_complete(progress, "c1")
    preview = build_agent_py_preview(
        progress,
        challenge_codes={"c1": 'print("Hello")'},
    )
    assert 'print("Hello")' in preview
    assert "# 🔒 完成 Skill Forge 解鎖" not in preview


def test_preview_uses_lab_code_when_voice_online() -> None:
    progress = DungeonProgress()
    mark_forge_challenge_complete(progress, "c1")
    mark_forge_challenge_complete(progress, "c2")
    mark_forge_challenge_complete(progress, "c3")
    lab = '''def speak():
    print("Hi there!")
    print("I am ready.")
speak()'''
    mark_forge_lab_complete(progress)
    preview = build_agent_py_preview(
        progress,
        challenge_codes={"c3": 'print("old")'},
        lab_code=lab,
    )
    assert "Hi there!" in preview
    assert 'print("old")' not in preview
