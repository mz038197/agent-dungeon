from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from agent_dungeon.core.cloud_paths import page_data_path, paths_for_user
from agent_dungeon.core.progress import (
    DungeonProgress,
    ModuleStatus,
    brain_module_online,
    voice_module_online,
)
from agent_dungeon.forge.forge_runtime.registry import build_platform_header

ModuleName = Literal["voice", "brain", "loop"]

_HEADER = build_platform_header(progress=None) + "\n"

_VOICE_START = "# === Voice 模組 ==="
_VOICE_END = "# === /Voice 模組 ==="
_BRAIN_START = "# === Brain 模組 ==="
_BRAIN_END = "# === /Brain 模組 ==="
_LOOP_START = "# === Loop 模組 ==="
_LOOP_END = "# === /Loop 模組 ==="

_MODULE_MARKERS: dict[ModuleName, tuple[str, str]] = {
    "voice": (_VOICE_START, _VOICE_END),
    "brain": (_BRAIN_START, _BRAIN_END),
    "loop": (_LOOP_START, _LOOP_END),
}

_CHAPTER_VOICE = "# --- Voice ---"
_CHAPTER_BRAIN = "# --- Brain ---"
_CHAPTER_LOOP = "# --- Loop ---"

_MAIN_ENTRY = '''if __name__ == "__main__":
    main()
'''

_MAIN_DEF_RE = re.compile(
    r"^def main\s*\([^)]*\)\s*:\s*\n(.*?)(?=^(?:def |if __name__|\Z))",
    re.MULTILINE | re.DOTALL,
)

_IF_NAME_LINE = re.compile(
    r"^(\s*)if __name__\s*==\s*(['\"])__main__\2\s*:\s*$"
)


def strip_if_name_guard_blocks(code: str) -> str:
    """移除所有 if __name__ == '__main__': 區塊（學員不應在編輯器撰寫）。"""
    lines = code.splitlines()
    result: list[str] = []
    i = 0
    while i < len(lines):
        match = _IF_NAME_LINE.match(lines[i])
        if match:
            base_indent = len(match.group(1))
            i += 1
            while i < len(lines):
                line = lines[i]
                if not line.strip():
                    i += 1
                    continue
                indent = len(line) - len(line.lstrip())
                if indent > base_indent:
                    i += 1
                    continue
                break
            continue
        result.append(lines[i])
        i += 1
    return "\n".join(result).rstrip()


def agent_py_path(google_sub: str) -> Path:
    return paths_for_user(google_sub).agent_py


def read_agent_py(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def write_agent_py(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def _section_pattern(start: str, end: str) -> re.Pattern[str]:
    return re.compile(
        re.escape(start) + r"\n?(.*?)\n?" + re.escape(end),
        re.DOTALL,
    )


def get_module_section(source: str, module: ModuleName) -> str:
    start, end = _MODULE_MARKERS[module]
    match = _section_pattern(start, end).search(source)
    if not match:
        return ""
    return match.group(1).strip()


def normalize_to_main_function(code: str) -> str:
    """將編輯器內容正規化為含 def main(): 的完整函式（不含 if __name__）。"""
    text = strip_if_name_guard_blocks(code.strip())
    if not text:
        return "def main():\n    pass"
    if re.search(r"^def main\s*\(", text, re.MULTILINE):
        return text
    indented = "\n".join(f"    {line}" if line.strip() else "" for line in text.splitlines())
    return f"def main():\n{indented}"


def extract_agent_main_source(source: str) -> str:
    """從 agent.py 取出 def main(): …（含 def 行）；舊版多區塊格式會自動合併。"""
    if not source.strip():
        return "def main():\n    pass"

    match = _MAIN_DEF_RE.search(source)
    if match:
        body = match.group(0).rstrip()
        if body:
            return body

    loop = get_module_section(source, "loop")
    if loop and not loop.startswith("# 🔒") and "def main" in loop:
        return normalize_to_main_function(loop)

    brain = get_module_section(source, "brain")
    if brain and not brain.startswith("# 🔒") and brain.strip():
        return normalize_to_main_function(brain)

    voice = get_module_section(source, "voice")
    if voice and not voice.startswith("# 🔒") and voice.strip():
        return normalize_to_main_function(voice)

    return "def main():\n    pass"


def read_agent_main_body(google_sub: str | None, *, progress: DungeonProgress | None = None) -> str:
    if google_sub is None:
        return "def main():\n    pass"
    migrate_page_data_to_agent_py(google_sub, progress=progress or DungeonProgress())
    path = agent_py_path(google_sub)
    return normalize_to_main_function(extract_agent_main_source(read_agent_py(path)))


def _marker_lines() -> str:
    return (
        f"{_VOICE_START}\n"
        f"{_CHAPTER_VOICE}\n"
        f"{_VOICE_END}\n\n"
        f"{_BRAIN_START}\n"
        f"{_CHAPTER_BRAIN}\n"
        f"{_BRAIN_END}\n\n"
        f"{_LOOP_START}\n"
        f"{_CHAPTER_LOOP}\n"
        f"{_LOOP_END}"
    )


def build_agent_py_from_main(main_source: str, *, progress: DungeonProgress | None = None) -> str:
    progress = progress or DungeonProgress()
    header = build_platform_header(progress=progress).strip()
    main_fn = normalize_to_main_function(main_source)
    return f"{header}\n\n{_marker_lines()}\n\n{main_fn}\n\n{_MAIN_ENTRY.strip()}\n"


def build_agent_py_template(*, progress: DungeonProgress | None = None) -> str:
    return build_agent_py_from_main("def main():\n    pass", progress=progress)


def ensure_agent_py(google_sub: str, *, progress: DungeonProgress | None = None) -> Path:
    path = agent_py_path(google_sub)
    if not path.is_file():
        write_agent_py(path, build_agent_py_template(progress=progress))
    return path


def _voice_challenge_code_from_page_data(page_data: dict) -> str:
    challenges = page_data.get("challenges")
    if not isinstance(challenges, dict):
        return ""
    for cid in ("c3", "c2", "c1"):
        raw = challenges.get(cid)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return ""


def sync_voice_forge_challenge_to_agent_py(
    google_sub: str,
    code: str,
    *,
    progress: DungeonProgress,
) -> Path:
    ensure_agent_py(google_sub, progress=progress)
    return write_agent_main_body(google_sub, code, progress=progress)


def backfill_voice_forge_to_agent_py(
    google_sub: str,
    challenge_codes: dict[str, str],
    *,
    progress: DungeonProgress,
) -> Path | None:
    from agent_dungeon.forge.challenges import voice_highest_challenge_code

    path = agent_py_path(google_sub)
    if path.is_file():
        main = extract_agent_main_source(read_agent_py(path))
        if main.strip() != "def main():\n    pass":
            return None
    code = voice_highest_challenge_code(challenge_codes)
    if not code.strip():
        return None
    return sync_voice_forge_challenge_to_agent_py(google_sub, code, progress=progress)


def write_agent_main_body(
    google_sub: str,
    main_source: str,
    *,
    progress: DungeonProgress | None = None,
) -> Path:
    path = ensure_agent_py(google_sub, progress=progress)
    write_agent_py(path, build_agent_py_from_main(main_source, progress=progress))
    return path


def sync_main_entry(google_sub: str, *, progress: DungeonProgress) -> None:
    """保留 API；統一 main 架構下 main 入口已在 build_agent_py_from_main 內。"""
    path = ensure_agent_py(google_sub, progress=progress)
    source = read_agent_py(path)
    main_body = extract_agent_main_source(source)
    write_agent_py(path, build_agent_py_from_main(main_body, progress=progress))


def _load_page_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _latest_challenge_code(page_data: dict, level: str) -> str:
    challenges = page_data.get("challenges")
    if not isinstance(challenges, dict):
        return ""
    for cid in ("c4", "c3", "c2", "c1"):
        raw = challenges.get(cid)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    code = page_data.get("code")
    if isinstance(code, str) and code.strip():
        return code.strip()
    return ""


def migrate_page_data_to_agent_py(google_sub: str, *, progress: DungeonProgress) -> Path:
    path = ensure_agent_py(google_sub, progress=progress)
    if extract_agent_main_source(read_agent_py(path)) != "def main():\n    pass":
        return path

    paths = paths_for_user(google_sub)
    voice_data = _load_page_json(page_data_path("Voice", paths))
    brain_data = _load_page_json(page_data_path("Brain", paths))
    loop_data = _load_page_json(page_data_path("Loop", paths))

    main_source = ""
    if loop_data and progress.modules.get("loop") != ModuleStatus.LOCKED:
        main_source = _latest_challenge_code(loop_data, "loop") or str(loop_data.get("code") or "")
    if not main_source.strip() and brain_data and brain_module_online(progress):
        main_source = _latest_challenge_code(brain_data, "brain") or str(brain_data.get("code") or "")
    if not main_source.strip() and voice_data and voice_module_online(progress):
        main_source = _voice_challenge_code_from_page_data(voice_data)

    if main_source.strip():
        write_agent_main_body(google_sub, main_source, progress=progress)
    return path


def write_module_section(
    google_sub: str,
    module: ModuleName,
    body: str,
    *,
    progress: DungeonProgress | None = None,
) -> Path:
    """向後相容：Forge 關卡完成後寫入統一 main()。"""
    return write_agent_main_body(google_sub, body, progress=progress)


def write_loop_module_body(
    google_sub: str,
    body: str,
    *,
    progress: DungeonProgress | None = None,
) -> Path:
    return write_agent_main_body(google_sub, body, progress=progress)


def read_module_for_editor(
    google_sub: str | None,
    module: ModuleName,
    *,
    fallback: str,
    progress: DungeonProgress | None = None,
) -> str:
    if google_sub is None:
        return fallback
    migrate_page_data_to_agent_py(google_sub, progress=progress or DungeonProgress())
    main_body = read_agent_main_body(google_sub, progress=progress)
    if main_body.strip() and main_body.strip() != "def main():\n    pass":
        return main_body
    return fallback
