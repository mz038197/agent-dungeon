from __future__ import annotations

from unittest.mock import patch

from agent_dungeon.forge.brain_runner import run_brain_forge_challenge, run_brain_forge_lab_code
from agent_dungeon.forge.llm_provider import DEFAULT_BRAIN_MODEL

DEFAULT_LAB_PROMPT = "你是一位英文助教，用簡單英文回答。"

_C1_CODE = """question = input("你想問什麼？ ")
print(question)
"""

_C2_CODE = f"""{_C1_CODE}
llm = Brain(model="{DEFAULT_BRAIN_MODEL}")
"""

_C3_CODE = f"""{_C2_CODE}
response = llm.invoke(question)
print(response)
"""


def test_brain_c1_requires_stdin() -> None:
    result = run_brain_forge_challenge(
        "c1",
        _C1_CODE,
        google_sub="sub-a",
        stdin_value="",
    )
    assert result.ok is False


def test_brain_c1_passes() -> None:
    result = run_brain_forge_challenge(
        "c1",
        _C1_CODE,
        google_sub="sub-a",
        stdin_value="Python 是什麼？",
    )
    assert result.ok is True
    assert "Python 是什麼？" in result.stdout


def test_brain_c2_passes() -> None:
    result = run_brain_forge_challenge(
        "c2",
        _C2_CODE,
        google_sub="sub-a",
        stdin_value="hi",
    )
    assert result.ok is True


def test_brain_c3_passes_with_mock_llm() -> None:
    with patch(
        "agent_dungeon.forge.llm_provider.invoke_llm_message",
        return_value="Python 是一種程式語言。",
    ):
        result = run_brain_forge_challenge(
            "c3",
            _C3_CODE,
            google_sub="sub-a",
            stdin_value="Python 是什麼？",
        )
    assert result.ok is True
    assert "Python 是一種程式語言。" in result.stdout


def test_brain_c3_requires_input() -> None:
    code_no_input = f"""llm = Brain(model="{DEFAULT_BRAIN_MODEL}")
response = llm.invoke("hi")
print(response)
"""
    with patch(
        "agent_dungeon.forge.llm_provider.invoke_llm_message",
        return_value="ok",
    ):
        result = run_brain_forge_challenge(
            "c3",
            code_no_input,
            google_sub="sub-a",
            stdin_value="test",
        )
    assert result.ok is False
    assert "input" in result.error


def test_brain_lab_requires_prompt_change() -> None:
    code = f"""prompt = "{DEFAULT_LAB_PROMPT}"
llm = Brain(model="{DEFAULT_BRAIN_MODEL}")
question = input("q")
response = llm.invoke(f"{{prompt}}\\n{{question}}")
print(response)
"""
    with patch(
        "agent_dungeon.forge.llm_provider.invoke_llm_message",
        return_value="Hello!",
    ):
        result = run_brain_forge_lab_code(
            code,
            google_sub="sub-a",
            stdin_value="test",
            default_prompt=DEFAULT_LAB_PROMPT,
        )
    assert result.ok is False
    assert "prompt" in result.error


def test_brain_lab_passes_with_changed_prompt() -> None:
    code = """prompt = "你是一位數學老師。"
llm = Brain(model="ollama_cloud@minimax-m3:cloud")
question = input("q")
response = llm.invoke(f"{prompt}\\n{question}")
print(response)
"""
    with patch(
        "agent_dungeon.forge.llm_provider.invoke_llm_message",
        return_value="1+1=2",
    ):
        result = run_brain_forge_lab_code(
            code,
            google_sub="sub-a",
            stdin_value="1+1?",
            default_prompt=DEFAULT_LAB_PROMPT,
        )
    assert result.ok is True
    assert "1+1=2" in result.stdout
