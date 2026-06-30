from __future__ import annotations

import ast
import io
from contextlib import redirect_stdout
from dataclasses import dataclass

from agent_dungeon.forge.challenges import CHALLENGE_IDS

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
    has_speak: bool = False


def _defines_speak(source: str) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    return any(
        isinstance(node, ast.FunctionDef) and node.name == "speak"
        for node in ast.walk(tree)
    )


def _calls_speak(source: str) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "speak":
                return True
    return False


def _speak_body_prints_hello(source: str) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "speak":
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
            if isinstance(arg, ast.Constant) and arg.value == "Hello":
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
    try:
        with redirect_stdout(buffer):
            exec(
                stripped,
                {"__builtins__": _SAFE_BUILTINS},
                namespace,
            )
    except SyntaxError as exc:
        return ForgeRunResult(ok=False, stdout=buffer.getvalue(), error=f"語法錯誤：{exc}")
    except Exception as exc:
        return ForgeRunResult(
            ok=False,
            stdout=buffer.getvalue(),
            error=f"執行錯誤：{exc}",
            has_speak=_defines_speak(stripped),
        )

    stdout = buffer.getvalue()
    lines = _non_empty_lines(stdout)
    speak_fn = namespace.get("speak")
    return ForgeRunResult(
        ok=True,
        stdout=stdout,
        line_count=len(lines),
        has_speak=callable(speak_fn),
    )


def _stdout_contains(stdout: str, expected: str) -> bool:
    return any(line.strip() == expected for line in stdout.splitlines())


def run_forge_challenge(challenge_id: str, source: str) -> ForgeRunResult:
    if challenge_id not in CHALLENGE_IDS:
        return ForgeRunResult(ok=False, stdout="", error="未知的 Challenge。")

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
        stripped = source.strip()
        if not _defines_speak(stripped):
            return ForgeRunResult(
                ok=False,
                stdout=stdout,
                error="需要定義 speak() 函式。",
                has_speak=False,
            )
        if not _speak_body_prints_hello(stripped):
            return ForgeRunResult(
                ok=False,
                stdout=stdout,
                error='speak() 函式內需要 print("Hello")。',
                has_speak=True,
            )
        return ForgeRunResult(
            ok=True,
            stdout=stdout,
            line_count=result.line_count,
            has_speak=True,
        )

    if challenge_id == "c3":
        stripped = source.strip()
        if not _defines_speak(stripped):
            return ForgeRunResult(
                ok=False,
                stdout=stdout,
                error="需要定義 speak() 函式。",
                has_speak=False,
            )
        if not _calls_speak(stripped):
            return ForgeRunResult(
                ok=False,
                stdout=stdout,
                error="請在程式碼中呼叫 speak()。",
                has_speak=True,
            )
        if not _stdout_contains(stdout, "Hello!"):
            return ForgeRunResult(
                ok=False,
                stdout=stdout,
                error='speak() 執行後需要輸出 Hello!',
                line_count=result.line_count,
                has_speak=True,
            )
        return ForgeRunResult(
            ok=True,
            stdout=stdout,
            line_count=result.line_count,
            has_speak=True,
        )

    return ForgeRunResult(ok=False, stdout=stdout, error="未知的 Challenge。")


def run_forge_lab_code(source: str) -> ForgeRunResult:
    stripped = source.strip()
    if not stripped:
        return ForgeRunResult(ok=False, stdout="", error="請先寫入程式碼。")

    if not _defines_speak(stripped):
        return ForgeRunResult(
            ok=False,
            stdout="",
            error="需要定義 speak() 函式。",
            has_speak=False,
        )

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
            has_speak=result.has_speak,
        )

    return ForgeRunResult(
        ok=True,
        stdout=stdout,
        line_count=len(lines),
        has_speak=result.has_speak,
    )
