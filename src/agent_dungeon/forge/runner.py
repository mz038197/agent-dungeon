from __future__ import annotations

import ast
import io
from contextlib import redirect_stdout
from dataclasses import dataclass

from agent_dungeon.forge.challenges import CHALLENGE_IDS
from agent_dungeon.forge.code_checks import has_main_call_in_main_guard

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
class ForgeRunResult:
    ok: bool
    stdout: str
    error: str = ""
    line_count: int = 0
    has_main: bool = False


_MAIN_REQUIRED_MSG = "需要定義 main() 函式（請寫 def main():，不要只寫在註解裡）。"


def _syntax_error_message(source: str) -> str | None:
    try:
        ast.parse(source)
    except SyntaxError as exc:
        return f"語法錯誤：{exc}"
    return None


def _require_main_for_challenge(source: str) -> ForgeRunResult | None:
    syntax_err = _syntax_error_message(source.strip())
    if syntax_err:
        return ForgeRunResult(ok=False, stdout="", error=syntax_err)
    if not _defines_main(source.strip()):
        return ForgeRunResult(
            ok=False,
            stdout="",
            error=_MAIN_REQUIRED_MSG,
            has_main=False,
        )
    return None


def _defines_main(source: str) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    return any(
        isinstance(node, ast.FunctionDef) and node.name == "main"
        for node in ast.walk(tree)
    )


def _main_body_prints_hello(source: str, *, exclamation: bool = False) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    expected = "Hello!" if exclamation else "Hello"
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "main":
            continue
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            func = child.func
            if not isinstance(func, ast.Name) or func.id != "print":
                continue
            if not child.args:
                continue
            arg = child.args[0]
            if isinstance(arg, ast.Constant) and arg.value == expected:
                return True
    return False


def _module_prints_hello(source: str, *, exclamation: bool = False) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    expected = "Hello!" if exclamation else "Hello"
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Name) or func.id != "print":
            continue
        if not node.args:
            continue
        arg = node.args[0]
        if isinstance(arg, ast.Constant) and arg.value == expected:
            return True
    return False


def _non_empty_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]


def _exec_sandbox(source: str) -> ForgeRunResult:
    stripped = source.strip()
    if not stripped:
        return ForgeRunResult(ok=False, stdout="", error="請先寫入程式碼。")

    buffer = io.StringIO()
    namespace: dict[str, object] = {}
    exec_source = stripped
    if _defines_main(stripped) and "if __name__" not in stripped:
        exec_source = f"{stripped}\n\nmain()"
    try:
        with redirect_stdout(buffer):
            exec(
                exec_source,
                {"__builtins__": _SAFE_BUILTINS, "__name__": "__main__"},
                namespace,
            )
    except SyntaxError as exc:
        return ForgeRunResult(ok=False, stdout=buffer.getvalue(), error=f"語法錯誤：{exc}")
    except Exception as exc:
        return ForgeRunResult(
            ok=False,
            stdout=buffer.getvalue(),
            error=f"執行錯誤：{exc}",
            has_main=_defines_main(stripped),
        )

    stdout = buffer.getvalue()
    lines = _non_empty_lines(stdout)
    return ForgeRunResult(
        ok=True,
        stdout=stdout,
        line_count=len(lines),
        has_main=_defines_main(stripped),
    )


def _stdout_contains(stdout: str, expected: str) -> bool:
    return any(line.strip() == expected for line in stdout.splitlines())


def run_forge_challenge(challenge_id: str, source: str) -> ForgeRunResult:
    if challenge_id not in CHALLENGE_IDS:
        return ForgeRunResult(ok=False, stdout="", error="未知的 Challenge。")

    if challenge_id in ("c2", "c3"):
        main_check = _require_main_for_challenge(source)
        if main_check is not None:
            return main_check

    result = _exec_sandbox(source)
    if not result.ok and result.error:
        return result

    stdout = result.stdout
    if challenge_id == "c1":
        if not _stdout_contains(stdout, "Hello"):
            return ForgeRunResult(
                ok=False,
                stdout=stdout,
                error='執行結果需要輸出 Hello（例如 print("Hello")）。',
                line_count=result.line_count,
            )
        return ForgeRunResult(ok=True, stdout=stdout, line_count=result.line_count)

    if challenge_id == "c2":
        if not _main_body_prints_hello(source.strip()):
            return ForgeRunResult(
                ok=False,
                stdout=stdout,
                error='main() 函式內需要 print("Hello")。',
                has_main=True,
            )
        return ForgeRunResult(
            ok=True,
            stdout=stdout,
            line_count=result.line_count,
            has_main=True,
        )

    if challenge_id == "c3":
        if not has_main_call_in_main_guard(source.strip()):
            return ForgeRunResult(
                ok=False,
                stdout=stdout,
                error='請在 `if __name__ == "__main__":` 區塊內呼叫 main()。',
                line_count=result.line_count,
                has_main=True,
            )
        if not _main_body_prints_hello(source.strip()):
            return ForgeRunResult(
                ok=False,
                stdout=stdout,
                error='main() 執行後需要輸出 Hello。',
                line_count=result.line_count,
                has_main=True,
            )
        return ForgeRunResult(
            ok=True,
            stdout=stdout,
            line_count=result.line_count,
            has_main=True,
        )

    return ForgeRunResult(ok=False, stdout=stdout, error="未知的 Challenge。")


def run_forge_lab_code(source: str) -> ForgeRunResult:
    stripped = source.strip()
    if not stripped:
        return ForgeRunResult(ok=False, stdout="", error="請先寫入程式碼。")

    main_check = _require_main_for_challenge(stripped)
    if main_check is not None:
        return main_check

    result = _exec_sandbox(stripped)
    if not result.ok:
        return result

    stdout = result.stdout
    lines = _non_empty_lines(stdout)
    if len(lines) < 2:
        return ForgeRunResult(
            ok=False,
            stdout=stdout,
            error="至少需要輸出兩句話（兩行 print 輸出）。",
            line_count=len(lines),
            has_main=result.has_main,
        )

    return ForgeRunResult(
        ok=True,
        stdout=stdout,
        line_count=len(lines),
        has_main=result.has_main,
    )
