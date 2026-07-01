from __future__ import annotations

import pytest

from agent_dungeon.core.progress import (
    LOOP_LEVEL_ID,
    ModuleStatus,
    agent_level,
    load_user_progress,
    mark_brain_forge_lab_complete,
    mark_forge_challenge_complete,
    mark_forge_lab_complete,
    mark_loop_forge_lab_complete,
    save_user_progress,
    skill_forge_complete,
)
from agent_dungeon.forge.agent_py_store import (
    ensure_agent_py,
    get_module_section,
    read_agent_py,
    write_loop_module_body,
    write_module_section,
)
from agent_dungeon.forge.loop_validator import validate_loop_challenge


@pytest.fixture
def peas_home(tmp_path, monkeypatch):
    home = tmp_path / "data"
    monkeypatch.setenv("PEAS_AGENT_HOME", str(home))
    return home


def _complete_voice(progress):
    for cid in ("c1", "c2", "c3"):
        mark_forge_challenge_complete(progress, cid)
    mark_forge_lab_complete(progress)


def test_brain_lab_complete_unlocks_loop(peas_home) -> None:
    progress = load_user_progress("sub-loop")
    _complete_voice(progress)
    for cid in ("c1", "c2", "c3"):
        mark_forge_challenge_complete(progress, cid, level_id="2")
    mark_brain_forge_lab_complete(progress)
    save_user_progress("sub-loop", progress)

    reloaded = load_user_progress("sub-loop")
    assert reloaded.modules["brain"] == ModuleStatus.COMPLETE
    assert reloaded.modules["loop"] == ModuleStatus.IN_PROGRESS
    assert reloaded.modules["memory"] == ModuleStatus.LOCKED
    assert agent_level(reloaded) == 2


def test_loop_lab_complete_unlocks_identity(peas_home) -> None:
    progress = load_user_progress("sub-loop2")
    _complete_voice(progress)
    mark_brain_forge_lab_complete(progress)
    for cid in ("c1", "c2", "c3"):
        mark_forge_challenge_complete(progress, cid, level_id=LOOP_LEVEL_ID)
    mark_loop_forge_lab_complete(progress)
    save_user_progress("sub-loop2", progress)

    reloaded = load_user_progress("sub-loop2")
    assert reloaded.modules["loop"] == ModuleStatus.COMPLETE
    assert reloaded.modules["identity"] == ModuleStatus.IN_PROGRESS
    assert agent_level(reloaded) == 3


def test_agent_py_store_sections(peas_home) -> None:
    progress = load_user_progress("sub-store")
    path = ensure_agent_py("sub-store", progress=progress)
    write_module_section("sub-store", "voice", 'print("hi")', progress=progress)
    text = read_agent_py(path)
    assert get_module_section(text, "voice") == 'print("hi")'


def test_loop_validator_c1(peas_home) -> None:
    progress = load_user_progress("sub-v")
    _complete_voice(progress)
    mark_brain_forge_lab_complete(progress)
    body = '''while True:
    question = input("> ")
    if question == "bye":
        break
    print(question)
'''
    path = write_loop_module_body("sub-v", body, progress=progress)
    result = validate_loop_challenge("c1", path)
    assert result.ok is True


def test_load_quests_eight_levels() -> None:
    from agent_dungeon.core.progress import load_quests_config

    payload = load_quests_config()
    assert len(payload["quests"]) == 8
    assert payload["quests"][2]["module"] == "loop"
