from __future__ import annotations

import json

import pytest

from agent_dungeon.core.progress import (
    ModuleStatus,
    agent_level,
    agent_level_view,
    load_user_progress,
    mark_forge_challenge_complete,
    mark_forge_lab_complete,
    save_user_progress,
    skill_forge_complete,
    voice_module_online,
)


@pytest.fixture
def peas_home(tmp_path, monkeypatch):
    home = tmp_path / "data"
    monkeypatch.setenv("PEAS_AGENT_HOME", str(home))
    return home


def test_default_progress_voice_in_progress(peas_home) -> None:
    progress = load_user_progress("sub-a")
    assert progress.modules["voice"] == ModuleStatus.IN_PROGRESS
    assert progress.modules["brain"] == ModuleStatus.LOCKED
    assert voice_module_online(progress) is False
    assert agent_level(progress) == 0
    level, next_hint, xp, xp_to_next = agent_level_view(progress)
    assert level == 0
    assert xp == 0
    assert xp_to_next == 100
    assert "第 1 關" in next_hint
    assert "說出第一句話" in next_hint


def test_forge_challenge_xp_increments(peas_home) -> None:
    progress = load_user_progress("sub-a")
    mark_forge_challenge_complete(progress, "c1")
    assert progress.xp == 33
    mark_forge_challenge_complete(progress, "c2")
    assert progress.xp == 66
    mark_forge_challenge_complete(progress, "c3")
    assert progress.xp == 99


def test_mark_forge_lab_complete(peas_home) -> None:
    progress = load_user_progress("sub-a")
    mark_forge_challenge_complete(progress, "c1")
    mark_forge_challenge_complete(progress, "c2")
    mark_forge_challenge_complete(progress, "c3")
    mark_forge_lab_complete(progress)
    save_user_progress("sub-a", progress)

    reloaded = load_user_progress("sub-a")
    assert reloaded.modules["voice"] == ModuleStatus.COMPLETE
    assert reloaded.modules["brain"] == ModuleStatus.IN_PROGRESS
    assert reloaded.levels["1"].mission_complete is True
    assert voice_module_online(reloaded) is True
    assert agent_level(reloaded) == 1
    assert reloaded.xp == 0
    assert reloaded.mp == 1
    _, next_hint, _, _ = agent_level_view(reloaded)
    assert "第 2 關" in next_hint

    raw = json.loads((peas_home / "users" / "sub-a" / "progress.json").read_text(encoding="utf-8"))
    assert raw["modules"]["voice"] == "complete"
    assert raw["modules"]["brain"] == "in_progress"


def test_forge_challenges_persist(peas_home) -> None:
    progress = load_user_progress("sub-a")
    mark_forge_challenge_complete(progress, "c1")
    mark_forge_challenge_complete(progress, "c2")
    save_user_progress("sub-a", progress)

    reloaded = load_user_progress("sub-a")
    assert reloaded.levels["1"].forge_challenges["c1"] is True
    assert reloaded.levels["1"].forge_challenges["c2"] is True
    assert reloaded.xp == 66
    assert skill_forge_complete(reloaded) is False
    assert voice_module_online(reloaded) is False
