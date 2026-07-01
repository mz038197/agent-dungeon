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
    assert "# === Voice 模組 ===" not in preview
    assert "# 🔒" not in preview
    assert "def main():" in preview


def test_preview_grows_with_c1() -> None:
    progress = DungeonProgress()
    mark_forge_challenge_complete(progress, "c1")
    preview = build_agent_py_preview(
        progress,
        challenge_codes={"c1": 'print("Hello")'},
    )
    assert 'print("Hello")' in preview
    assert "# === Voice 模組 ===" not in preview


def test_preview_uses_c3_not_lab_code_when_voice_online() -> None:
    progress = DungeonProgress()
    mark_forge_challenge_complete(progress, "c1")
    mark_forge_challenge_complete(progress, "c2")
    mark_forge_challenge_complete(progress, "c3")
    c3_code = """def main():
    print("Hello")

if __name__ == "__main__":
    main()
"""
    lab = """def main():
    print("Hi there!")
    print("I am ready.")
"""
    mark_forge_lab_complete(progress)
    preview = build_agent_py_preview(
        progress,
        challenge_codes={"c3": c3_code},
        lab_code=lab,
    )
    assert 'print("Hello")' in preview
    assert "Hi there!" not in preview


def test_preview_strips_nested_if_name_in_main_body() -> None:
    from agent_dungeon.forge.challenges import _VOICE_C3_LEGACY_IF_NAME

    progress = DungeonProgress()
    mark_forge_challenge_complete(progress, "c1")
    mark_forge_challenge_complete(progress, "c2")
    polluted = f"""def main():
    print("Hello")
{_VOICE_C3_LEGACY_IF_NAME}
"""
    preview = build_agent_py_preview(
        progress,
        challenge_codes={"c2": polluted, "c3": polluted},
    )
    assert preview.count('if __name__ == "__main__":') == 1
    assert "    if __name__" not in preview
    assert 'print("Hello")' in preview
