from __future__ import annotations


def main_source_has_full_line_comments(main_source: str) -> bool:
    for line in main_source.splitlines():
        if line.strip().startswith("#"):
            return True
    return False


def strip_comments_from_source(code: str) -> str:
    """剝除整行 # 註解，供 agent.py 寫入（中欄 Forge 原文不含註解）。"""
    from agent_dungeon.forge.agent_py_store import (
        normalize_to_main_function,
        strip_if_name_guard_blocks,
    )

    text = strip_if_name_guard_blocks(code.strip())
    if not text:
        return "def main():\n    pass"

    kept = [line for line in text.splitlines() if not line.strip().startswith("#")]
    while kept and not kept[-1].strip():
        kept.pop()
    result = "\n".join(kept).rstrip()
    if not result:
        return "def main():\n    pass"
    normalized = normalize_to_main_function(result)
    body_lines = [
        line
        for line in normalized.splitlines()[1:]
        if line.strip() and line.strip() != "pass"
    ]
    if normalized.strip().startswith("def main") and not body_lines:
        return "def main():\n    pass"
    return normalized


def agent_py_source_has_main_comments(full_source: str) -> bool:
    from agent_dungeon.forge.agent_py_store import extract_agent_main_source

    return main_source_has_full_line_comments(extract_agent_main_source(full_source))
