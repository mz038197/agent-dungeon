from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class TerminalState(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    EXITED = "exited"


@dataclass
class AgentTerminalSession:
    agent_py: Path
    google_sub: str
    process: subprocess.Popen[str] | None = None
    stdout_buffer: str = ""
    stderr_buffer: str = ""
    state: TerminalState = TerminalState.IDLE
    exit_code: int | None = None
    turn_count: int = 0
    input_lines: list[str] = field(default_factory=list)
    _reader_stop: threading.Event = field(default_factory=threading.Event, repr=False)
    _reader_thread: threading.Thread | None = field(default=None, repr=False)

    def effective_output(self) -> str:
        parts: list[str] = []
        if self.stdout_buffer.strip():
            parts.append(self.stdout_buffer.rstrip())
        if self.stderr_buffer.strip():
            parts.append(self.stderr_buffer.rstrip())
        return "\n".join(parts)


def _env_for_subprocess(google_sub: str) -> dict[str, str]:
    env = os.environ.copy()
    env["AGENT_DUNGEON_USER_SUB"] = google_sub
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _poll_reader(session: AgentTerminalSession) -> None:
    proc = session.process
    if proc is None or proc.stdout is None:
        return
    while not session._reader_stop.is_set():
        if proc.poll() is not None:
            remaining = proc.stdout.read()
            if remaining:
                session.stdout_buffer += remaining
            break
        chunk = proc.stdout.read(1)
        if chunk:
            session.stdout_buffer += chunk
        else:
            time.sleep(0.05)
    if proc.stderr is not None:
        err = proc.stderr.read()
        if err:
            session.stderr_buffer += err
    session.exit_code = proc.poll()
    session.state = TerminalState.EXITED


def start_agent(agent_py: Path, *, google_sub: str) -> AgentTerminalSession:
    if not agent_py.is_file():
        raise FileNotFoundError(f"找不到 agent.py：{agent_py}")
    session = AgentTerminalSession(agent_py=agent_py, google_sub=google_sub)
    session.process = subprocess.Popen(
        [sys.executable, str(agent_py.resolve())],
        cwd=str(agent_py.parent),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_env_for_subprocess(google_sub),
        bufsize=1,
    )
    session.state = TerminalState.RUNNING
    session._reader_stop.clear()
    session._reader_thread = threading.Thread(
        target=_poll_reader,
        args=(session,),
        daemon=True,
    )
    session._reader_thread.start()
    return session


def poll_output(session: AgentTerminalSession) -> str:
    if session.process is not None and session.process.poll() is not None:
        session.state = TerminalState.EXITED
        session.exit_code = session.process.returncode
    return session.effective_output()


def send_input(session: AgentTerminalSession, line: str) -> None:
    if session.state != TerminalState.RUNNING or session.process is None:
        raise RuntimeError("Agent 未在執行中。")
    if session.process.stdin is None:
        raise RuntimeError("無法寫入 stdin。")
    stripped = line.strip()
    if stripped and stripped.lower() != "bye":
        session.turn_count += 1
        session.input_lines.append(stripped)
    session.process.stdin.write(line if line.endswith("\n") else line + "\n")
    session.process.stdin.flush()


def stop_agent(session: AgentTerminalSession) -> None:
    session._reader_stop.set()
    proc = session.process
    if proc is None:
        session.state = TerminalState.EXITED
        return
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)
    session.exit_code = proc.returncode
    session.state = TerminalState.EXITED
    if session._reader_thread is not None:
        session._reader_thread.join(timeout=1)


def is_running(session: AgentTerminalSession) -> bool:
    if session.process is None:
        return False
    if session.process.poll() is not None:
        session.state = TerminalState.EXITED
        session.exit_code = session.process.returncode
        return False
    return session.state == TerminalState.RUNNING
