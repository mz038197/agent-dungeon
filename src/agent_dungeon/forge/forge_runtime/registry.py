from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from agent_dungeon.core.progress import MODULE_IDS, ModuleStatus
from agent_dungeon.forge.adapters.brain import render_standalone_brain_module

if TYPE_CHECKING:
    from agent_dungeon.core.progress import DungeonProgress

_AGENT_PY_DOC = '"""Agent Dungeon — 你的 Agent（agent.py）"""'


@dataclass(frozen=True)
class RuntimeObjectSpec:
    module_id: str
    symbols: tuple[str, ...]
    export_filename: str
    platform_import: str
    platform_binding: str
    export_import: str
    render_standalone: Callable[[], str]


def _brain_spec() -> RuntimeObjectSpec:
    return RuntimeObjectSpec(
        module_id="brain",
        symbols=("Brain",),
        export_filename="brain.py",
        platform_import="from agent_dungeon.forge.agent_runtime import get_brain_class",
        platform_binding=(
            'Brain = get_brain_class(os.environ.get("AGENT_DUNGEON_USER_SUB") or None)'
        ),
        export_import="from runtime import Brain",
        render_standalone=render_standalone_brain_module,
    )


RUNTIME_REGISTRY: tuple[RuntimeObjectSpec, ...] = (_brain_spec(),)

_RUNTIME_BY_MODULE: dict[str, RuntimeObjectSpec] = {
    spec.module_id: spec for spec in RUNTIME_REGISTRY
}


def runtime_spec_for_module(module_id: str) -> RuntimeObjectSpec | None:
    return _RUNTIME_BY_MODULE.get(module_id)


def runtime_symbols_for_progress(progress: DungeonProgress) -> tuple[str, ...]:
    symbols: list[str] = []
    for spec in RUNTIME_REGISTRY:
        status = progress.modules.get(spec.module_id, ModuleStatus.LOCKED)
        if status in (ModuleStatus.IN_PROGRESS, ModuleStatus.COMPLETE):
            symbols.extend(spec.symbols)
    return tuple(symbols)


def build_platform_header(*, progress: DungeonProgress | None = None) -> str:
    del progress  # Brain 在 Brain 模組上線後即注入；與現行 agent.py 行為一致
    lines = [_AGENT_PY_DOC, "import os", ""]
    seen_imports: set[str] = set()
    bindings: list[str] = []
    for spec in RUNTIME_REGISTRY:
        if spec.platform_import not in seen_imports:
            lines.append(spec.platform_import)
            seen_imports.add(spec.platform_import)
        bindings.append(spec.platform_binding)
    if bindings:
        lines.append("")
        lines.extend(bindings)
    return "\n".join(lines)


def build_export_header(*, progress: DungeonProgress) -> str:
    symbols = runtime_symbols_for_progress(progress)
    if not symbols:
        return _AGENT_PY_DOC
    if len(symbols) == 1:
        return f"{_AGENT_PY_DOC}\nfrom runtime import {symbols[0]}"
    joined = ", ".join(symbols)
    return f"{_AGENT_PY_DOC}\nfrom runtime import {joined}"


def export_runtime_modules(*, progress: DungeonProgress) -> dict[str, str]:
    files: dict[str, str] = {}
    exports: list[str] = []
    for spec in RUNTIME_REGISTRY:
        if progress.modules.get(spec.module_id) != ModuleStatus.COMPLETE:
            continue
        rel_path = f"runtime/{spec.export_filename}"
        files[rel_path] = spec.render_standalone()
        exports.extend(spec.symbols)

    if exports:
        init_lines = ['"""Forge runtime — 畢業匯出教學物件。"""']
        for spec in RUNTIME_REGISTRY:
            if progress.modules.get(spec.module_id) != ModuleStatus.COMPLETE:
                continue
            module_name = spec.export_filename.removesuffix(".py")
            for symbol in spec.symbols:
                init_lines.append(f"from runtime.{module_name} import {symbol}")
        init_lines.append("")
        init_lines.append("__all__ = [")
        for symbol in exports:
            init_lines.append(f'    "{symbol}",')
        init_lines.append("]")
        init_lines.append("")
        files["runtime/__init__.py"] = "\n".join(init_lines)
    return files


_PLATFORM_HEADER_PATTERN = re.compile(
    r'^"""Agent Dungeon — 你的 Agent（agent\.py）"""\s*\n'
    r"(?:import os\s*\n)?"
    r"(?:from agent_dungeon\.forge\.agent_runtime import get_brain_class\s*\n)?"
    r'(?:Brain = get_brain_class\(os\.environ\.get\("AGENT_DUNGEON_USER_SUB"\) or None\)\s*\n)?',
    re.MULTILINE,
)


def rewrite_agent_py_header(source: str, *, progress: DungeonProgress) -> str:
    header = build_export_header(progress=progress)
    stripped = source.lstrip("\ufeff")
    if _PLATFORM_HEADER_PATTERN.match(stripped):
        body = _PLATFORM_HEADER_PATTERN.sub("", stripped, count=1)
        return f"{header}\n\n{body.lstrip()}"
    return source
