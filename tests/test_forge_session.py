from __future__ import annotations

import streamlit as st

from agent_dungeon.forge.forge_session import clear_forge_level_session


def test_clear_forge_level_session_removes_editor_keys(monkeypatch) -> None:
    state: dict[str, object] = {
        "brain_forge_c1_code": "old",
        "brain_forge_c1_stdout": "out",
        "brain_forge_c1_awaiting_collapse": True,
        "brain_forge_c2_code": "keep",
        "brain_forge_stdin": "hi",
        "unrelated": 1,
    }
    monkeypatch.setattr(st, "session_state", state, raising=False)

    clear_forge_level_session("brain_forge", ("c1",))

    assert "brain_forge_c1_code" not in state
    assert "brain_forge_c1_stdout" not in state
    assert "brain_forge_c1_awaiting_collapse" not in state
    assert state["brain_forge_c2_code"] == "keep"
    assert "brain_forge_stdin" not in state
    assert state["unrelated"] == 1
