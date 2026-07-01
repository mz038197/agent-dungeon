from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from agent_dungeon.core.cloud_paths import page_data_path, paths_for_user
from agent_dungeon.core.progress import (
    BRAIN_LEVEL_ID,
    DungeonProgress,
    ModuleStatus,
    VOICE_LEVEL_ID,
    brain_module_online,
    voice_module_online,
)
from agent_dungeon.forge.challenges import BRAIN_LEGACY_LAB_CODE, VOICE_LEGACY_LAB_CODE
from agent_dungeon.forge.llm_provider import DEFAULT_BRAIN_MODEL

ModuleName = Literal["voice", "brain", "loop"]

_HEADER = '''\
"""Agent Dungeon — 你的 Agent（agent.py）"""
import os

from agent_dungeon.forge.agent_runtime import get_brain_class

Brain = get_brain_class(os.environ.get("AGENT_DUNGEON_USER_SUB") or None)
'''

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

_DEFAULT_VOICE_BODY = VOICE_LEGACY_LAB_CODE.strip()

_DEFAULT_BRAIN_BODY = BRAIN_LEGACY_LAB_CODE.strip()

_DEFAULT_LOOP_BODY = f'''\
def main():
    """Loop 模組：持續對話（Forge Lab 自由完成）。"""
    prompt = "你是一位友善助教。"
    llm = Brain(model="{DEFAULT_BRAIN_MODEL}")
    while True:
        question = input("> ")
        if question == "bye":
            break
        if not question.strip():
            continue
        response = llm.invoke(f"{{prompt}}\\n\\n問題：{{question}}")
        print(response)


if __name__ == "__main__":
    main()
'''.strip()

_DEFAULT_MAIN_VOICE = """\
if __name__ == "__main__":
    speak()
"""

_DEFAULT_MAIN_BRAIN = """\
if __name__ == "__main__":
    prompt = "你是一位英文助教，用簡單英文回答。"
    llm = Brain(model="{model}")
    question = input("你想問什麼？ ")
    response = llm.invoke(f"{{prompt}}\\n\\n問題：{{question}}")
    print(response)
""".format(model=DEFAULT_BRAIN_MODEL)


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


def _replace_section(source: str, module: ModuleName, body: str) -> str:
    start, end = _MODULE_MARKERS[module]
    block = f"{start}\n{body.strip()}\n{end}"
    pattern = _section_pattern(start, end)
    if pattern.search(source):
        return pattern.sub(block, source, count=1)
    return source.rstrip() + "\n\n" + block + "\n"


def _default_body(module: ModuleName) -> str:
    if module == "voice":
        return _DEFAULT_VOICE_BODY
    if module == "brain":
        return _DEFAULT_BRAIN_BODY
    return _DEFAULT_LOOP_BODY


def _main_for_progress(progress: DungeonProgress) -> str:
    if progress.modules.get("brain") == ModuleStatus.COMPLETE or brain_module_online(progress):
        loop_body = _DEFAULT_LOOP_BODY
        if "def main():" in loop_body:
            return 'if __name__ == "__main__":\n    main()\n'
    if progress.modules.get("voice") == ModuleStatus.COMPLETE or brain_module_online(progress):
        if brain_module_online(progress):
            return _DEFAULT_MAIN_BRAIN.strip() + "\n"
        return _DEFAULT_MAIN_VOICE.strip() + "\n"
    return _DEFAULT_MAIN_VOICE.strip() + "\n"


def build_agent_py_template(*, progress: DungeonProgress | None = None) -> str:
    progress = progress or DungeonProgress()
    voice_body = _default_body("voice") if voice_module_online(progress) else "# 🔒 完成 Voice 後解鎖"
    brain_body = (
        _default_body("brain")
        if brain_module_online(progress)
        else ("# 🔒 完成 Voice 後解鎖" if progress.modules.get("voice") != ModuleStatus.COMPLETE else "# 🔒 完成 Skill Forge 解鎖")
    )
    loop_body = (
        _DEFAULT_LOOP_BODY.split("if __name__")[0].strip()
        if progress.modules.get("brain") == ModuleStatus.COMPLETE
        else "# 🔒 完成 Brain 後解鎖"
    )
    main_block = _main_for_progress(progress)
    return (
        f"{_HEADER.strip()}\n\n"
        f"{_VOICE_START}\n{voice_body}\n{_VOICE_END}\n\n"
        f"{_BRAIN_START}\n{brain_body}\n{_BRAIN_END}\n\n"
        f"{_LOOP_START}\n{loop_body}\n{_LOOP_END}\n\n"
        f"{main_block.strip()}\n"
    )


def ensure_agent_py(google_sub: str, *, progress: DungeonProgress | None = None) -> Path:
    path = agent_py_path(google_sub)
    if not path.is_file():
        write_agent_py(path, build_agent_py_template(progress=progress))
    return path


def write_module_section(
    google_sub: str,
    module: ModuleName,
    body: str,
    *,
    progress: DungeonProgress | None = None,
) -> Path:
    path = ensure_agent_py(google_sub, progress=progress)
    source = read_agent_py(path)
    updated = _replace_section(source, module, body)
    if module == "brain" and get_module_section(updated, "brain").startswith("# 🔒"):
        updated = _replace_section(updated, "brain", body)
    if module == "voice":
        updated = _replace_section(updated, "voice", body)
    write_agent_py(path, updated)
    return path


def sync_main_entry(google_sub: str, *, progress: DungeonProgress) -> None:
    path = ensure_agent_py(google_sub, progress=progress)
    source = read_agent_py(path)
    main_block = _main_for_progress(progress)
    if re.search(r"if __name__ == ['\"]__main__['\"]", source):
        source = re.sub(
            r"\nif __name__ == ['\"]__main__['\"]:.*\Z",
            "",
            source,
            flags=re.DOTALL,
        ).rstrip()
    loop_section = get_module_section(source, "loop")
    if progress.modules.get("brain") == ModuleStatus.COMPLETE and "def main():" in loop_section:
        main_block = 'if __name__ == "__main__":\n    main()\n'
    write_agent_py(path, source + "\n\n" + main_block.strip() + "\n")


def _load_page_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def migrate_page_data_to_agent_py(google_sub: str, *, progress: DungeonProgress) -> Path:
    path = ensure_agent_py(google_sub, progress=progress)
    paths = paths_for_user(google_sub)
    voice_data = _load_page_json(page_data_path("Voice", paths))
    brain_data = _load_page_json(page_data_path("Brain", paths))

    source = read_agent_py(path)
    voice_code = voice_data.get("code")
    if isinstance(voice_code, str) and voice_code.strip() and voice_module_online(progress):
        source = _replace_section(source, "voice", voice_code.strip())
    brain_code = brain_data.get("code")
    if isinstance(brain_code, str) and brain_code.strip() and brain_module_online(progress):
        source = _replace_section(source, "brain", brain_code.strip())
    write_agent_py(path, source)
    sync_main_entry(google_sub, progress=progress)
    return path


def write_loop_module_body(
    google_sub: str,
    body: str,
    *,
    progress: DungeonProgress | None = None,
) -> Path:
    text = body.strip()
    if "def main" not in text:
        indented = "\n".join(f"    {line}" if line.strip() else "" for line in text.splitlines())
        text = f"def main():\n{indented}"
    return write_module_section(google_sub, "loop", text, progress=progress)


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
    path = agent_py_path(google_sub)
    section = get_module_section(read_agent_py(path), module)
    if section and not section.startswith("# 🔒"):
        return section
    return fallback
