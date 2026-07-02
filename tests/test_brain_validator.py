from __future__ import annotations

from pathlib import Path

from agent_dungeon.forge.agent_py_store import build_agent_py_from_main, write_agent_py
from agent_dungeon.forge.agent_terminal import AgentTerminalSession, TerminalState
from agent_dungeon.forge.brain_validator import validate_brain_challenge, validate_brain_forge_lab
from agent_dungeon.forge.llm_provider import DEFAULT_BRAIN_MODEL

DEFAULT_LAB_PROMPT = "你是一位英文助教，用簡單英文回答。"

_C1_MAIN = '''def main():
    question = input("你想問什麼？ ")
    print(question)
'''

_C2_MAIN = f'''def main():
    question = input("你想問什麼？ ")
    print(question)
    llm = Brain(model="{DEFAULT_BRAIN_MODEL}")
'''

_C3_MAIN = f'''def main():
    question = input("你想問什麼？ ")
    llm = Brain(model="{DEFAULT_BRAIN_MODEL}")
    response = llm.invoke(question)
    print(response)
'''


def _write_agent_py(tmp_path: Path, main_source: str) -> Path:
    agent_py = tmp_path / "agent.py"
    write_agent_py(agent_py, build_agent_py_from_main(main_source))
    return agent_py


def _session_with_input(*, stdout: str, input_line: str) -> AgentTerminalSession:
    session = AgentTerminalSession(
        agent_py=Path("agent.py"),
        google_sub="sub-a",
        stdout_buffer=stdout,
        state=TerminalState.EXITED,
    )
    session.input_lines.append(input_line)
    return session


def test_brain_c1_requires_terminal_input(tmp_path: Path) -> None:
    agent_py = _write_agent_py(tmp_path, _C1_MAIN)
    result = validate_brain_challenge("c1", agent_py, session=None)
    assert result.ok is False
    assert "終端機" in result.error


def test_brain_c1_requires_echo(tmp_path: Path) -> None:
    agent_py = _write_agent_py(tmp_path, _C1_MAIN)
    session = _session_with_input(stdout="wrong", input_line="Python 是什麼？")
    result = validate_brain_challenge("c1", agent_py, session=session)
    assert result.ok is False
    assert "print" in result.error


def test_brain_c1_passes(tmp_path: Path) -> None:
    agent_py = _write_agent_py(tmp_path, _C1_MAIN)
    session = _session_with_input(stdout="Python 是什麼？\n", input_line="Python 是什麼？")
    result = validate_brain_challenge("c1", agent_py, session=session)
    assert result.ok is True


def test_brain_c2_passes_without_terminal(tmp_path: Path) -> None:
    agent_py = _write_agent_py(tmp_path, _C2_MAIN)
    result = validate_brain_challenge("c2", agent_py, session=None)
    assert result.ok is True


def test_brain_c2_requires_brain_constructor(tmp_path: Path) -> None:
    agent_py = _write_agent_py(tmp_path, _C1_MAIN)
    result = validate_brain_challenge("c2", agent_py, session=None)
    assert result.ok is False
    assert "Brain" in result.error


def test_brain_c3_requires_terminal_stdout(tmp_path: Path) -> None:
    agent_py = _write_agent_py(tmp_path, _C3_MAIN)
    session = AgentTerminalSession(
        agent_py=agent_py,
        google_sub="sub-a",
        input_lines=["Python 是什麼？"],
    )
    result = validate_brain_challenge("c3", agent_py, session=session)
    assert result.ok is False
    assert "print" in result.error


def test_brain_c3_passes_with_stdout(tmp_path: Path) -> None:
    agent_py = _write_agent_py(tmp_path, _C3_MAIN)
    session = _session_with_input(
        stdout="Python 是一種程式語言。\n",
        input_line="Python 是什麼？",
    )
    result = validate_brain_challenge("c3", agent_py, session=session)
    assert result.ok is True


def test_brain_lab_requires_prompt_change(tmp_path: Path) -> None:
    code = f'''def main():
    prompt = "{DEFAULT_LAB_PROMPT}"
    llm = Brain(model="{DEFAULT_BRAIN_MODEL}")
    question = input("q")
    response = llm.invoke(f"{{prompt}}\\n{{question}}")
    print(response)
'''
    agent_py = _write_agent_py(tmp_path, code)
    session = _session_with_input(stdout="Hello!", input_line="hi")
    result = validate_brain_forge_lab(
        agent_py,
        session=session,
        default_prompt=DEFAULT_LAB_PROMPT,
    )
    assert result.ok is False
    assert "prompt" in result.error


def test_brain_lab_passes(tmp_path: Path) -> None:
    code = '''def main():
    prompt = "你是一位數學老師。"
    llm = Brain(model="ollama_cloud@minimax-m3:cloud")
    question = input("q")
    response = llm.invoke(f"{prompt}\\n{question}")
    print(response)
'''
    agent_py = _write_agent_py(tmp_path, code)
    session = _session_with_input(stdout="1+1=2\n", input_line="1+1?")
    result = validate_brain_forge_lab(
        agent_py,
        session=session,
        default_prompt=DEFAULT_LAB_PROMPT,
    )
    assert result.ok is True
