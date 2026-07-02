from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from agent_dungeon.forge.agent_py_store import extract_agent_main_source, read_agent_py
from agent_dungeon.forge.agent_terminal import AgentTerminalSession
from agent_dungeon.forge.code_checks import has_input_call
from agent_dungeon.forge.llm_provider import model_in_allowlist

BRAIN_CHALLENGE_IDS = ("c1", "c2", "c3")


@dataclass(frozen=True)
class BrainValidationResult:
    ok: bool
    error: str = ""


def _parse_tree(source: str) -> ast.AST | None:
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _brain_model_from_source(source: str) -> str | None:
    tree = _parse_tree(source)
    if tree is None:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Name) or func.id != "Brain":
            continue
        for keyword in node.keywords:
            if keyword.arg == "model":
                arg = keyword.value
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    return arg.value
        if node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                return arg.value
    return None


def _has_invoke_call(source: str) -> bool:
    tree = _parse_tree(source)
    if tree is None:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "invoke":
            return True
    return False


def _invoke_message_nonempty(source: str) -> bool:
    tree = _parse_tree(source)
    if tree is None:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "invoke":
            continue
        if not node.args:
            continue
        arg = node.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return bool(arg.value.strip())
        if isinstance(arg, ast.Name):
            return True
        if isinstance(arg, ast.JoinedStr):
            return True
    return False


def _prompt_assignment(source: str) -> str | None:
    tree = _parse_tree(source)
    if tree is None:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "prompt":
                value = node.value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    return value.value
    return None


def _brain_source_from_agent_py(agent_py: Path) -> str:
    full = read_agent_py(agent_py)
    return extract_agent_main_source(full)


def _stdout_contains_input_echo(stdout: str, stdin_value: str) -> bool:
    if not stdin_value.strip():
        return False
    needle = stdin_value.strip()
    for line in stdout.splitlines():
        stripped = line.strip()
        if stripped == needle or stripped.endswith(needle):
            return True
    return False


def _terminal_stdout(session: AgentTerminalSession | None) -> str:
    if session is None:
        return ""
    return session.effective_output()


def validate_brain_challenge(
    challenge_id: str,
    agent_py: Path,
    *,
    session: AgentTerminalSession | None = None,
) -> BrainValidationResult:
    if challenge_id not in BRAIN_CHALLENGE_IDS:
        return BrainValidationResult(ok=False, error="未知的 Challenge。")

    source = _brain_source_from_agent_py(agent_py)
    stripped = source.strip()
    if not stripped:
        return BrainValidationResult(ok=False, error="請先寫入程式碼。")

    stdout = _terminal_stdout(session)

    if challenge_id == "c1":
        if not has_input_call(stripped):
            return BrainValidationResult(
                ok=False,
                error="需要呼叫 input() 讀取使用者輸入。",
            )
        if session is None or not session.input_lines:
            return BrainValidationResult(
                ok=False,
                error="請在終端機輸入內容並按 Enter 送出。",
            )
        last_input = session.input_lines[-1]
        if not _stdout_contains_input_echo(stdout, last_input):
            return BrainValidationResult(
                ok=False,
                error="請用 print 顯示 input() 讀到的內容。",
            )
        return BrainValidationResult(ok=True)

    if challenge_id == "c2":
        model = _brain_model_from_source(stripped)
        if model is None:
            return BrainValidationResult(
                ok=False,
                error='需要建立 Brain，例如 llm = Brain(model="...")。',
            )
        if not model_in_allowlist(model):
            return BrainValidationResult(
                ok=False,
                error=f"model {model!r} 不在允許清單中。",
            )
        if not has_input_call(stripped):
            return BrainValidationResult(
                ok=False,
                error="請保留 C1 的 input() 程式。",
            )
        return BrainValidationResult(ok=True)

    if challenge_id == "c3":
        if not has_input_call(stripped):
            return BrainValidationResult(ok=False, error="需要 input()。")
        model = _brain_model_from_source(stripped)
        if model is None or not model_in_allowlist(model):
            return BrainValidationResult(
                ok=False,
                error='需要有效的 Brain(model="...")。',
            )
        if not _has_invoke_call(stripped):
            return BrainValidationResult(
                ok=False,
                error="需要呼叫 llm.invoke(...)。",
            )
        if not _invoke_message_nonempty(stripped):
            return BrainValidationResult(
                ok=False,
                error="invoke 需要非空訊息參數。",
            )
        if session is None or not session.input_lines:
            return BrainValidationResult(
                ok=False,
                error="請在終端機輸入問題並執行，看到 Brain 回覆後再確認過關。",
            )
        if not stdout.strip():
            return BrainValidationResult(
                ok=False,
                error="請 print Brain 的回覆，完成 Brain 安裝。",
            )
        return BrainValidationResult(ok=True)

    return BrainValidationResult(ok=False, error="未知的 Challenge。")


def validate_brain_forge_lab(
    agent_py: Path,
    *,
    session: AgentTerminalSession | None = None,
    default_prompt: str,
) -> BrainValidationResult:
    source = _brain_source_from_agent_py(agent_py)
    stripped = source.strip()
    if not stripped:
        return BrainValidationResult(ok=False, error="請先寫入程式碼。")

    prompt_value = _prompt_assignment(stripped)
    if prompt_value is None:
        return BrainValidationResult(ok=False, error="需要 prompt 變數。")
    if prompt_value.strip() == default_prompt.strip():
        return BrainValidationResult(
            ok=False,
            error="請修改 prompt（與預設不同），打造你的 Agent 角色。",
        )

    model = _brain_model_from_source(stripped)
    if model is None or not model_in_allowlist(model):
        return BrainValidationResult(ok=False, error='需要有效的 Brain(model="...")。')
    if not _has_invoke_call(stripped):
        return BrainValidationResult(ok=False, error="需要 llm.invoke(...)。")

    stdout = _terminal_stdout(session)
    if session is None or not session.input_lines:
        return BrainValidationResult(
            ok=False,
            error="請在終端機輸入問題並執行，看到 Brain 回覆後再完成 Forge Lab。",
        )
    if not stdout.strip():
        return BrainValidationResult(ok=False, error="請 print Brain 的回覆。")
    return BrainValidationResult(ok=True)
