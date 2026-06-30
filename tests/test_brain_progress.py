from __future__ import annotations

import pytest

from agent_dungeon.core.progress import (
    BRAIN_LEVEL_ID,
    ModuleStatus,
    agent_level,
    load_user_progress,
    mark_brain_forge_lab_complete,
    mark_forge_challenge_complete,
    mark_forge_lab_complete,
    save_user_progress,
    skill_forge_complete,
)


@pytest.fixture
def peas_home(tmp_path, monkeypatch):
    home = tmp_path / "data"
    monkeypatch.setenv("PEAS_AGENT_HOME", str(home))
    return home


def _complete_voice(progress):
    for cid in ("c1", "c2", "c3"):
        mark_forge_challenge_complete(progress, cid)
    mark_forge_lab_complete(progress)


def test_brain_forge_after_voice(peas_home) -> None:
    progress = load_user_progress("sub-b")
    _complete_voice(progress)
    save_user_progress("sub-b", progress)

    reloaded = load_user_progress("sub-b")
    assert reloaded.modules["brain"] == ModuleStatus.IN_PROGRESS
    assert skill_forge_complete(reloaded, level_id=BRAIN_LEVEL_ID) is False


def test_brain_lab_complete_unlocks_memory(peas_home) -> None:
    progress = load_user_progress("sub-b")
    _complete_voice(progress)
    for cid in ("c1", "c2", "c3"):
        mark_forge_challenge_complete(progress, cid, level_id=BRAIN_LEVEL_ID)
    mark_brain_forge_lab_complete(progress)
    save_user_progress("sub-b", progress)

    reloaded = load_user_progress("sub-b")
    assert reloaded.modules["brain"] == ModuleStatus.COMPLETE
    assert reloaded.modules["memory"] == ModuleStatus.IN_PROGRESS
    assert agent_level(reloaded) == 2
