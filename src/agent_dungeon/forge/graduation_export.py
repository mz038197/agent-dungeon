from __future__ import annotations

import io
import json
import zipfile
from datetime import UTC, datetime
from typing import Any

from agent_dungeon.core.progress import (
    MODULE_IDS,
    DungeonProgress,
    ModuleStatus,
    is_dungeon_graduated,
)
from agent_dungeon.forge.adapters.brain import DEFAULT_BRAIN_MODEL
from agent_dungeon.forge.agent_py_store import agent_py_path, extract_agent_main_source, read_agent_py
from agent_dungeon.forge.forge_runtime.registry import (
    export_runtime_modules,
    rewrite_agent_py_header,
)

_EXPORT_REQUIREMENTS = """\
langchain-openai>=0.3
langchain-core>=0.3
python-dotenv>=1.0
"""

_ENV_EXAMPLE = f"""\
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
BRAIN_MODEL={DEFAULT_BRAIN_MODEL}
BRAIN_TEMPERATURE=0.2
BRAIN_OUTPUT_VERSION=responses/v1
BRAIN_REASONING_EFFORT=medium
"""

_README = """\
# 我的 Agent 專案

這是你在 Agent Dungeon 八關全通後匯出的 agent 專案。課堂使用的 `Brain` 與 `invoke()` API 都保留在本專案中。

## 本機執行

1. 建立虛擬環境並安裝依賴：

   ```bash
   pip install -r requirements.txt
   ```

2. 複製環境變數範本並填入 API key：

   ```bash
   cp .env.example .env
   ```

3. 執行 agent：

   ```bash
   python agent.py
   ```

## 次日 AI Coding 課

在**同一個專案根目錄**執行課程提供的 installer（in-place 安裝）。Installer 會讀取 `manifest.json` 的 `entrypoint`，直接使用本目錄的 `agent.py`，不會替換你的程式。

詳細步驟以課程講義為準。
"""


def _agent_sections(source: str) -> dict[str, str]:
    main_body = extract_agent_main_source(source)
    if main_body.strip() and main_body.strip() != "def main():\n    pass":
        return {"main": main_body}
    return {}


def _build_manifest(
    *,
    progress: DungeonProgress,
    google_sub: str,
    display_name: str,
    sections: dict[str, str],
) -> dict[str, Any]:
    runtime_modules: dict[str, Any] = {}
    for rel_path in export_runtime_modules(progress=progress):
        if not rel_path.startswith("runtime/") or not rel_path.endswith(".py"):
            continue
        if rel_path == "runtime/__init__.py":
            continue
        module_key = rel_path.removeprefix("runtime/").removesuffix(".py")
        runtime_modules[module_key] = {
            "file": rel_path,
            "symbols": ["Brain"] if module_key == "brain" else [],
        }

    return {
        "schema_version": 1,
        "source": "agent-dungeon",
        "install_mode": "in_place",
        "project_root": ".",
        "entrypoint": "agent.py",
        "runtime": {
            "package": "runtime",
            "modules": runtime_modules,
        },
        "installer": {
            "expected_cwd": "project_root",
            "shell_entry": "shell/app.py",
            "loads_student_agent": True,
        },
        "artifacts": {
            "agent_py": "agent.py",
            "sections": sections,
        },
        "student": {
            "google_sub": google_sub,
            "display_name": display_name,
        },
        "dungeon": {
            "modules_complete": [
                module_id
                for module_id in MODULE_IDS
                if progress.modules.get(module_id) == ModuleStatus.COMPLETE
            ],
            "exported_at": datetime.now(UTC).isoformat(),
        },
    }


def build_graduation_zip(
    *,
    google_sub: str,
    progress: DungeonProgress,
    display_name: str = "",
) -> bytes:
    if not is_dungeon_graduated(progress):
        raise ValueError("尚未八關全通，無法匯出畢業專案。")

    agent_path = agent_py_path(google_sub)
    source = read_agent_py(agent_path)
    if not source.strip():
        raise ValueError("找不到 agent.py 內容。")

    exported_agent_py = rewrite_agent_py_header(source, progress=progress)
    runtime_files = export_runtime_modules(progress=progress)
    sections = _agent_sections(source)
    manifest = _build_manifest(
        progress=progress,
        google_sub=google_sub,
        display_name=display_name,
        sections=sections,
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("agent.py", exported_agent_py.rstrip() + "\n")
        archive.writestr("requirements.txt", _EXPORT_REQUIREMENTS.rstrip() + "\n")
        archive.writestr(".env.example", _ENV_EXAMPLE.rstrip() + "\n")
        archive.writestr("README.md", _README.rstrip() + "\n")
        archive.writestr(
            "manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        )
        archive.writestr(
            "progress.json",
            json.dumps(manifest["dungeon"], ensure_ascii=False, indent=2) + "\n",
        )
        for rel_path, content in sorted(runtime_files.items()):
            archive.writestr(rel_path, content.rstrip() + "\n")

    return buffer.getvalue()


def graduation_zip_filename(*, display_name: str, google_sub: str) -> str:
    slug = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in display_name.strip())
    slug = slug.strip("-_") or google_sub[:8] or "student"
    return f"{slug}-agent.zip"
