from __future__ import annotations

import pytest

from agent_dungeon.core.dungeon_context import build_dungeon_extra_context
from agent_dungeon.core.progress import (
    DungeonProgress,
    mark_forge_challenge_complete,
    skill_forge_complete,
)


def test_skill_forge_complete_requires_all_challenges() -> None:
    progress = DungeonProgress()
    assert skill_forge_complete(progress) is False

    mark_forge_challenge_complete(progress, "c1")
    assert skill_forge_complete(progress) is False

    mark_forge_challenge_complete(progress, "c2")
    mark_forge_challenge_complete(progress, "c3")
    assert skill_forge_complete(progress) is True


def test_build_dungeon_extra_context_includes_left_and_center() -> None:
    progress = DungeonProgress()
    mark_forge_challenge_complete(progress, "c1")
    extra = build_dungeon_extra_context(
        progress,
        page_name="Voice",
        google_sub="sub-test",
        current_module="voice",
    )
    assert "【目前頁面】Voice" in extra
    assert "【左欄等級】" in extra
    assert "【中欄SkillForge_C1】完成" in extra
    assert "【中欄SkillForge_C2】進行中" in extra
    assert "【共享資料檔】" in extra
    assert "voice.json" in extra
