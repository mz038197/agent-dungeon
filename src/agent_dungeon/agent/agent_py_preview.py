from __future__ import annotations

from pathlib import Path

from agent_dungeon.core.progress import DungeonProgress
from agent_dungeon.forge.agent_py_store import (
    agent_py_path as resolve_agent_py_path,
    build_agent_py_template,
    ensure_agent_py,
    read_agent_py,
    sanitize_agent_py_if_needed,
)


def build_agent_py_preview(
    progress: DungeonProgress,
    *,
    agent_py_path: str | None = None,
    google_sub: str | None = None,
) -> str:
    """右欄預覽：直接顯示磁碟上的 workspace/agent.py。"""
    path_str = agent_py_path
    if google_sub and not path_str:
        path_str = str(resolve_agent_py_path(google_sub))

    if path_str:
        path = Path(path_str)
        if path.is_file():
            return path.read_text(encoding="utf-8")

    if google_sub:
        sanitize_agent_py_if_needed(google_sub, progress=progress)
        path = ensure_agent_py(google_sub, progress=progress)
        return read_agent_py(path)

    return build_agent_py_template(progress=progress)
