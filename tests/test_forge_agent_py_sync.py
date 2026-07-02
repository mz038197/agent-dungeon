from __future__ import annotations

from pathlib import Path

import pytest

from agent_dungeon.core.progress import DungeonProgress
from agent_dungeon.forge.agent_py_store import (
    extract_agent_main_source,
    read_agent_py,
    sync_voice_forge_challenge_to_agent_py,
)
from agent_dungeon.forge.challenges import (
    BRAIN_FORGE_CHALLENGES,
    LOOP_FORGE_CHALLENGES,
    brain_challenge_codes_from_stored,
    brain_editor_code_needs_refresh,
    loop_challenge_codes_from_stored,
    merge_brain_challenge_stored_with_session,
    merge_loop_challenge_stored_with_session,
)
from agent_dungeon.forge.llm_provider import DEFAULT_BRAIN_MODEL


def test_merge_brain_includes_in_progress_c2_session() -> None:
    c2_session = f'''def main():
    # --- 本關：建立 Brain ---
    llm = Brain(model="{DEFAULT_BRAIN_MODEL}")
    question = input("q")
    print(question)
'''
    stored = {"c1": "done", "c2": BRAIN_FORGE_CHALLENGES[1].default_code}
    merged = merge_brain_challenge_stored_with_session(
        stored,
        session_overrides={"c2": c2_session},
        completed={"c1": True, "c2": False},
    )
    assert merged is not None
    assert DEFAULT_BRAIN_MODEL in merged["c2"]
    codes = brain_challenge_codes_from_stored(
        merged,
        completed={"c1": True, "c2": False},
    )
    assert DEFAULT_BRAIN_MODEL in codes["c2"]


def test_brain_c2_with_model_does_not_need_refresh() -> None:
    expected = f'''def main():
{BRAIN_FORGE_CHALLENGES[1].default_code.strip()}
    question = input("q")
    print(question)
'''
    current = f'''def main():
    llm = Brain(model="{DEFAULT_BRAIN_MODEL}")
    question = input("q")
    print(question)
'''
    assert (
        brain_editor_code_needs_refresh(
            BRAIN_FORGE_CHALLENGES[1],
            current,
            expected=expected,
            completed=False,
        )
        is False
    )


def test_merge_loop_includes_in_progress_session() -> None:
    loop_session = """def main():
    while True:
        question = input("> ")
        print(question)
"""
    stored = {"c1": LOOP_FORGE_CHALLENGES[0].default_code}
    merged = merge_loop_challenge_stored_with_session(
        stored,
        session_overrides={"c1": loop_session},
        completed={"c1": False},
    )
    assert merged is not None
    assert "while True" in merged["c1"]
    codes = loop_challenge_codes_from_stored(merged, completed={"c1": False})
    assert "while True" in codes["c1"]


def test_brain_c2_session_writes_model_to_agent_py(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    google_sub = "test-brain-sync"
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

    editor = f'''def main():
    llm = Brain(model="{DEFAULT_BRAIN_MODEL}")
    question = input("q")
    print(question)
'''
    sync_voice_forge_challenge_to_agent_py(google_sub, editor, progress=progress)
    from agent_dungeon.forge.agent_py_store import agent_py_path

    main = extract_agent_main_source(read_agent_py(agent_py_path(google_sub)))
    assert DEFAULT_BRAIN_MODEL in main
    assert "llm = Brain" in main
