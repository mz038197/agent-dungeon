from __future__ import annotations

import ast
import io
from contextlib import redirect_stdout
from dataclasses import dataclass

from agent_dungeon.forge.code_checks import has_brain_constructor, has_input_call
from agent_dungeon.forge.llm_provider import DEFAULT_BRAIN_MODEL, make_brain_class, model_in_allowlist

BRAIN_CHALLENGE_IDS = ("c1", "c2", "c3")

_SAFE_BUILTINS = {
    "print": print,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "len": len,
    "range": range,
    "True": True,
    "False": False,
    "None": None,
}


@dataclass(frozen=True)
class BrainForgeRunResult:
    ok: bool
    stdout: str
    error: str = ""
    llm_response: str = ""


def _non_empty_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]


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


def _has_brain_constructor(source: str) -> bool:
    return has_brain_constructor(source)


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


def _exec_brain_sandbox(
    source: str,
    *,
    google_sub: str | None,
    stdin_value: str,
) -> BrainForgeRunResult:
    stripped = source.strip()
    if not stripped:
        return BrainForgeRunResult(ok=False, stdout="", error="請先寫入程式碼。")

    buffer = io.StringIO()
    input_values = [stdin_value]
    Brain = make_brain_class(google_sub=google_sub)

    def sandbox_input(prompt: str = "") -> str:
        if input_values:
            return input_values.pop(0)
        return stdin_value

    namespace: dict[str, object] = {"Brain": Brain, "input": sandbox_input}
    try:
        with redirect_stdout(buffer):
            exec(
                stripped,
                {"__builtins__": _SAFE_BUILTINS},
                namespace,
            )
    except SyntaxError as exc:
        return BrainForgeRunResult(ok=False, stdout=buffer.getvalue(), error=f"語法錯誤：{exc}")
    except Exception as exc:
        message = str(exc).strip() or "執行錯誤"
        return BrainForgeRunResult(ok=False, stdout=buffer.getvalue(), error=message)

    return BrainForgeRunResult(ok=True, stdout=buffer.getvalue())


def _stdout_contains_input_echo(stdout: str, stdin_value: str) -> bool:
    if not stdin_value.strip():
        return False
    needle = stdin_value.strip()
    for line in stdout.splitlines():
        stripped = line.strip()
        if stripped == needle or stripped.endswith(needle):
            return True
    return False


def run_brain_forge_challenge(
    challenge_id: str,
    source: str,
    *,
    google_sub: str | None,
    stdin_value: str,
) -> BrainForgeRunResult:
    if challenge_id not in BRAIN_CHALLENGE_IDS:
        return BrainForgeRunResult(ok=False, stdout="", error="未知的 Challenge。")

    if not stdin_value.strip() and challenge_id in {"c1", "c3"}:
        return BrainForgeRunResult(ok=False, stdout="", error="請先在輸入框填寫 input() 要讀的值。")

    result = _exec_brain_sandbox(source, google_sub=google_sub, stdin_value=stdin_value)
    if not result.ok:
        return result

    stdout = result.stdout
    stripped = source.strip()

    if challenge_id == "c1":
        if not has_input_call(stripped):
            return BrainForgeRunResult(
                ok=False,
                stdout=stdout,
                error="需要呼叫 input() 讀取使用者輸入。",
            )
        if not _stdout_contains_input_echo(stdout, stdin_value):
            return BrainForgeRunResult(
                ok=False,
                stdout=stdout,
                error="請用 print 顯示 input() 讀到的內容。",
            )
        return BrainForgeRunResult(ok=True, stdout=stdout)

    if challenge_id == "c2":
        model = _brain_model_from_source(stripped)
        if model is None:
            return BrainForgeRunResult(
                ok=False,
                stdout=stdout,
                error='需要建立 Brain，例如 llm = Brain(model="...")。',
            )
        if not model_in_allowlist(model):
            return BrainForgeRunResult(
                ok=False,
                stdout=stdout,
                error=f"model {model!r} 不在允許清單中。",
            )
        if not has_input_call(stripped):
            return BrainForgeRunResult(
                ok=False,
                stdout=stdout,
                error="請保留 C1 的 input() 程式。",
            )
        return BrainForgeRunResult(ok=True, stdout=stdout)

    if challenge_id == "c3":
        if not has_input_call(stripped):
            return BrainForgeRunResult(ok=False, stdout=stdout, error="需要 input()。")
        model = _brain_model_from_source(stripped)
        if model is None or not model_in_allowlist(model):
            return BrainForgeRunResult(
                ok=False,
                stdout=stdout,
                error="需要有效的 Brain(model=\"...\")。",
            )
        if not _has_invoke_call(stripped):
            return BrainForgeRunResult(
                ok=False,
                stdout=stdout,
                error="需要呼叫 llm.invoke(...)。",
            )
        if not _invoke_message_nonempty(stripped):
            return BrainForgeRunResult(
                ok=False,
                stdout=stdout,
                error="invoke 需要非空訊息參數。",
            )
        if not stdout.strip():
            return BrainForgeRunResult(
                ok=False,
                stdout=stdout,
                error="請 print Brain 的回覆，完成 Brain 安裝。",
            )
        return BrainForgeRunResult(ok=True, stdout=stdout)

    return BrainForgeRunResult(ok=False, stdout=stdout, error="未知的 Challenge。")


def run_brain_forge_lab_code(
    source: str,
    *,
    google_sub: str | None,
    stdin_value: str,
    default_prompt: str,
) -> BrainForgeRunResult:
    stripped = source.strip()
    if not stripped:
        return BrainForgeRunResult(ok=False, stdout="", error="請先寫入程式碼。")
    if not stdin_value.strip():
        return BrainForgeRunResult(ok=False, stdout="", error="請先在輸入框填寫 input() 要讀的值。")

    prompt_value = _prompt_assignment(stripped)
    if prompt_value is None:
        return BrainForgeRunResult(ok=False, stdout="", error="需要 prompt 變數。")
    if prompt_value.strip() == default_prompt.strip():
        return BrainForgeRunResult(
            ok=False,
            stdout="",
            error="請修改 prompt（與預設不同），打造你的 Agent 角色。",
        )

    model = _brain_model_from_source(stripped)
    if model is None or not model_in_allowlist(model):
        return BrainForgeRunResult(ok=False, stdout="", error="需要有效的 Brain(model=\"...\")。")
    if not _has_invoke_call(stripped):
        return BrainForgeRunResult(ok=False, stdout="", error="需要 llm.invoke(...)。")

    result = _exec_brain_sandbox(stripped, google_sub=google_sub, stdin_value=stdin_value)
    if not result.ok:
        return result
    if not result.stdout.strip():
        return BrainForgeRunResult(
            ok=False,
            stdout=result.stdout,
            error="請 print Brain 的回覆。",
        )
    return BrainForgeRunResult(ok=True, stdout=result.stdout)
