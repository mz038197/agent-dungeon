from __future__ import annotations

from agent_dungeon.forge.agent_terminal import AgentTerminalSession, TerminalState, send_input
from unittest.mock import MagicMock


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
