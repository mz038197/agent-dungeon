from __future__ import annotations

import pytest

from agent_dungeon.forge.runner import run_forge_challenge, run_forge_lab_code


def test_challenge_c1_passes() -> None:
    result = run_forge_challenge("c1", 'print("Hello")')
    assert result.ok is True
    assert "Hello" in result.stdout


def test_challenge_c1_fails_wrong_output() -> None:
    result = run_forge_challenge("c1", 'print("Hi")')
    assert result.ok is False


def test_challenge_c2_passes_with_main() -> None:
    code = """def main():
    print("Hello")
"""
    result = run_forge_challenge("c2", code)
    assert result.ok is True
    assert result.has_main is True


def test_challenge_c2_fails_without_main() -> None:
    result = run_forge_challenge("c2", 'print("Hello")')
    assert result.ok is False
    assert "main" in result.error
    assert "註解" in result.error


def test_challenge_c2_syntax_error_before_main_message() -> None:
    code = """def main():
    # only comment
"""
    result = run_forge_challenge("c2", code)
    assert result.ok is False
    assert "語法錯誤" in result.error


def test_challenge_c2_fails_with_main_in_comment_only() -> None:
    result = run_forge_challenge("c2", "# def main():\n# print(\"Hello\")")
    assert result.ok is False
    assert "main" in result.error


def test_challenge_c2_fails_without_print_hello() -> None:
    code = """def main():
    print("Hi")
"""
    result = run_forge_challenge("c2", code)
    assert result.ok is False
    assert 'print("Hello")' in result.error


def test_challenge_c3_passes() -> None:
    code = """def main():
    print("Hello!")

if __name__ == "__main__":
    main()
"""
    result = run_forge_challenge("c3", code)
    assert result.ok is True


def test_challenge_c3_requires_exclamation() -> None:
    code = """def main():
    print("Hello")

if __name__ == "__main__":
    main()
"""
    result = run_forge_challenge("c3", code)
    assert result.ok is False


def test_challenge_c3_fails_without_main_call_in_guard() -> None:
    code = """def main():
    print("Hello!")

if __name__ == "__main__":
    pass
"""
    result = run_forge_challenge("c3", code)
    assert result.ok is False
    assert "__main__" in result.error


def test_challenge_c3_fails_main_call_outside_guard() -> None:
    code = """def main():
    print("Hello!")

main()
"""
    result = run_forge_challenge("c3", code)
    assert result.ok is False
    assert "__main__" in result.error


def test_challenge_c3_fails_main_call_in_comment_only() -> None:
    code = """def main():
    print("Hello!")

if __name__ == "__main__":
    # main()
    pass
"""
    result = run_forge_challenge("c3", code)
    assert result.ok is False
    assert "__main__" in result.error


def test_forge_lab_passes_with_main_and_two_lines() -> None:
    code = """def main():
    print("Hello")
    print("World")
"""
    result = run_forge_lab_code(code)
    assert result.ok is True
    assert result.line_count >= 2
    assert result.has_main is True


def test_forge_lab_fails_without_main() -> None:
    result = run_forge_lab_code('print("only one line")\nprint("second")')
    assert result.ok is False
    assert "main" in result.error.lower()


def test_forge_lab_fails_with_one_line() -> None:
    code = """def main():
    print("only one")
"""
    result = run_forge_lab_code(code)
    assert result.ok is False
    assert "兩" in result.error


def test_forge_lab_syntax_error() -> None:
    result = run_forge_lab_code("def main(\n")
    assert result.ok is False
    assert result.error
