from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

from agent_dungeon.forge.agent_terminal import (
    AgentTerminalSession,
    TerminalState,
    send_input,
    start_agent,
    stop_agent,
)


def test_send_input_records_input_lines() -> None:
    session = AgentTerminalSession(
        agent_py=__file__,
        google_sub="sub-a",
        state=TerminalState.RUNNING,
    )
    proc = MagicMock()
    proc.stdin = MagicMock()
    session.process = proc

    send_input(session, "  hello world  ")
    assert session.input_lines == ["hello world"]
    assert session.turn_count == 1

    send_input(session, "bye")
    assert session.input_lines == ["hello world"]
    assert session.turn_count == 1


def test_reader_captures_input_prompt_before_stdin(tmp_path: Path) -> None:
    script = tmp_path / "prompt_wait.py"
    script.write_text('input("你的問題: ")\n', encoding="utf-8")

    session = start_agent(script, google_sub="test-sub")
    try:
        deadline = time.time() + 3.0
        while time.time() < deadline:
            if "你的問題:" in session.stdout_buffer:
                break
            time.sleep(0.05)
        assert "你的問題: " in session.stdout_buffer
    finally:
        stop_agent(session)
