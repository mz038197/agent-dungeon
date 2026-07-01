from __future__ import annotations

from agent_dungeon.forge.agent_py_store import (
    build_agent_py_from_main,
    normalize_to_main_function,
    strip_if_name_guard_blocks,
)
from agent_dungeon.forge.challenges import _VOICE_C3_LEGACY_IF_NAME


def test_strip_if_name_removes_nested_guard_in_main() -> None:
    polluted = """def main():
    print("Hello")
    if __name__ == "__main__":
        main()
"""
    cleaned = strip_if_name_guard_blocks(polluted)
    assert "if __name__" not in cleaned
    assert 'print("Hello")' in cleaned


def test_normalize_strips_trailing_module_guard() -> None:
    polluted = """def main():
    print("Hello!")

if __name__ == "__main__":
    main()
"""
    result = normalize_to_main_function(polluted)
    assert result.count("if __name__") == 0
    assert 'print("Hello!")' in result


def test_build_agent_py_has_single_main_guard() -> None:
    polluted = f"""def main():
    print("Hello")
{_VOICE_C3_LEGACY_IF_NAME}
"""
    content = build_agent_py_from_main(polluted)
    assert content.count('if __name__ == "__main__":') == 1
    assert "    if __name__" not in content


def test_build_agent_py_omits_module_markers() -> None:
    content = build_agent_py_from_main('def main():\n    print("Hello")')
    assert "# === Voice 模組 ===" not in content
    assert "# === Brain 模組 ===" not in content
    assert "# === Loop 模組 ===" not in content
    assert 'print("Hello")' in content
