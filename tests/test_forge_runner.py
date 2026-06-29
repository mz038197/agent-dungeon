from __future__ import annotations

import pytest

from forge_runner import run_forge_challenge, run_forge_lab_code


def test_challenge_c1_passes() -> None:
    result = run_forge_challenge("c1", 'print("Hello")')
    assert result.ok is True
    assert "Hello" in result.stdout


def test_challenge_c1_fails_wrong_output() -> None:
    result = run_forge_challenge("c1", 'print("Hi")')
    assert result.ok is False


def test_challenge_c2_passes_without_call() -> None:
    code = """def speak():
    print("Hello")
"""
    result = run_forge_challenge("c2", code)
    assert result.ok is True


def test_challenge_c2_fails_without_print_hello() -> None:
    code = """def speak():
    print("Hi")
"""
    result = run_forge_challenge("c2", code)
    assert result.ok is False
    assert 'print("Hello")' in result.error


def test_challenge_c2_passes_with_call() -> None:
    code = """def speak():
    print("Hello")

speak()
"""
    result = run_forge_challenge("c2", code)
    assert result.ok is True


def test_challenge_c3_passes() -> None:
    code = """def speak():
    print("Hello!")

speak()
"""
    result = run_forge_challenge("c3", code)
    assert result.ok is True


def test_challenge_c3_requires_exclamation() -> None:
    code = """def speak():
    print("Hello")

speak()
"""
    result = run_forge_challenge("c3", code)
    assert result.ok is False


def test_forge_lab_passes_with_speak_and_two_lines() -> None:
    code = """def speak():
    print("Hello")
    print("World")

speak()
"""
    result = run_forge_lab_code(code)
    assert result.ok is True
    assert result.line_count >= 2
    assert result.has_speak is True


def test_forge_lab_fails_without_speak() -> None:
    result = run_forge_lab_code('print("only one line")\nprint("second")')
    assert result.ok is False
    assert "speak" in result.error.lower()


def test_forge_lab_fails_with_one_line() -> None:
    code = """def speak():
    print("only one")

speak()
"""
    result = run_forge_lab_code(code)
    assert result.ok is False
    assert "兩" in result.error


def test_forge_lab_syntax_error() -> None:
    result = run_forge_lab_code("def speak(\n")
    assert result.ok is False
    assert result.error
