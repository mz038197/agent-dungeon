from __future__ import annotations

from agent_dungeon.forge.forge_sanitize import strip_comments_from_source


def test_strip_comments_removes_forge_hints() -> None:
    raw = """def main():
    # TODO: 用 input() 取得 question，再用 print 顯示
    # Code Here #
    # --- 本關：建立 Brain ---
    # llm = Brain(model="gpt-4.1-mini")
    print("Hello")
    question = input("> ")
"""
    clean = strip_comments_from_source(raw)
    assert "TODO" not in clean
    assert "Code Here" not in clean
    assert "本關" not in clean
    assert "llm = Brain" not in clean
    assert 'print("Hello")' in clean
    assert "input(" in clean


def test_strip_comments_removes_voice_hint() -> None:
    raw = """def main():
    # 使用 print 函式 輸出 "Hello" !
    print("Hello")
"""
    clean = strip_comments_from_source(raw)
    assert "#" not in clean
    assert 'print("Hello")' in clean


def test_strip_comments_empty_becomes_pass() -> None:
    raw = """def main():
    # only comments
    # Code Here #
"""
    clean = strip_comments_from_source(raw)
    assert clean.strip() == "def main():\n    pass"


def test_strip_comments_module_level_hints_before_main() -> None:
    raw = """# --- 本關：建立 main() ---
# 提示：用 def 定義函式
def main():
    print("Hello")
"""
    clean = strip_comments_from_source(raw)
    assert "本關" not in clean
    assert "提示" not in clean
    assert 'print("Hello")' in clean
