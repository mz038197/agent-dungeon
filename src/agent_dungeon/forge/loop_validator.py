from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from agent_dungeon.forge.agent_py_store import get_module_section, read_agent_py
from agent_dungeon.forge.agent_terminal import AgentTerminalSession


@dataclass(frozen=True)
class LoopValidationResult:
    ok: bool
    error: str = ""


def _parse(source: str) -> ast.AST | None:
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _has_while_loop(source: str) -> bool:
    tree = _parse(source)
    if tree is None:
        return False
    return any(isinstance(node, ast.While) for node in ast.walk(tree))


def _has_break(source: str) -> bool:
    tree = _parse(source)
    if tree is None:
        return False
    return any(isinstance(node, ast.Break) for node in ast.walk(tree))


def _has_continue(source: str) -> bool:
    tree = _parse(source)
    if tree is None:
        return False
    return any(isinstance(node, ast.Continue) for node in ast.walk(tree))


def _has_input_in_while(source: str) -> bool:
    tree = _parse(source)
    if tree is None:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                func = child.func
                if isinstance(func, ast.Name) and func.id == "input":
                    return True
    return False


def _has_invoke(source: str) -> bool:
    tree = _parse(source)
    if tree is None:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "invoke":
                return True
    return False


def _loop_source_from_agent_py(agent_py: Path) -> str:
    full = read_agent_py(agent_py)
    loop = get_module_section(full, "loop")
    brain = get_module_section(full, "brain")
    if loop and not loop.startswith("# 🔒"):
        return loop
    if brain and not brain.startswith("# 🔒"):
        return brain
    return full


def validate_loop_challenge(
    challenge_id: str,
    agent_py: Path,
    *,
    session: AgentTerminalSession | None = None,
    min_turns: int = 2,
) -> LoopValidationResult:
    source = _loop_source_from_agent_py(agent_py)
    if not source.strip():
        return LoopValidationResult(ok=False, error="agent.py Loop 區塊為空。")

    if challenge_id == "c1":
        if not _has_while_loop(source):
            return LoopValidationResult(ok=False, error="需要 while 迴圈。")
        if not _has_break(source):
            return LoopValidationResult(ok=False, error="需要 break 離開方式（例如 bye）。")
        if session is not None and session.turn_count < min_turns:
            return LoopValidationResult(
                ok=False,
                error=f"請在終端機至少對話 {min_turns} 輪（不含 bye），目前 {session.turn_count} 輪。",
            )
        return LoopValidationResult(ok=True)

    if challenge_id == "c2":
        if not _has_input_in_while(source):
            return LoopValidationResult(ok=False, error="input() 需在 while 迴圈內。")
        if not _has_invoke(source):
            return LoopValidationResult(ok=False, error="需要 llm.invoke(...)。")
        if session is not None and session.turn_count < min_turns:
            return LoopValidationResult(
                ok=False,
                error=f"請在終端機至少對話 {min_turns} 輪，目前 {session.turn_count} 輪。",
            )
        return LoopValidationResult(ok=True)

    if challenge_id == "c3":
        if not _has_continue(source):
            return LoopValidationResult(ok=False, error="需要 continue（例如空字串跳過）。")
        if session is not None and session.turn_count < 1:
            return LoopValidationResult(ok=False, error="請在終端機至少完成一輪有效對話。")
        return LoopValidationResult(ok=True)

    return LoopValidationResult(ok=False, error="未知的 Challenge。")


def validate_loop_forge_lab(
    agent_py: Path,
    *,
    session: AgentTerminalSession | None = None,
) -> LoopValidationResult:
    source = _loop_source_from_agent_py(agent_py)
    if not _has_while_loop(source):
        return LoopValidationResult(ok=False, error="Forge Lab 需要 while 迴圈。")
    if not _has_break(source):
        return LoopValidationResult(ok=False, error="需要 bye 離開指令。")
    lowered = source.lower()
    if "help" not in lowered:
        return LoopValidationResult(ok=False, error="Forge Lab 需要 help 指令處理。")
    if session is not None and session.turn_count < 2:
        return LoopValidationResult(
            ok=False,
            error="請在終端機至少對話 2 輪後再完成 Forge Lab。",
        )
    return LoopValidationResult(ok=True)
