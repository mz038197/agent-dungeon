from __future__ import annotations

import os

from agent_dungeon.forge.adapters.brain import make_brain_class
from agent_dungeon.forge.forge_runtime.registry import RUNTIME_REGISTRY

_ENV_USER_SUB = "AGENT_DUNGEON_USER_SUB"


def runtime_google_sub() -> str | None:
    raw = os.environ.get(_ENV_USER_SUB, "").strip()
    return raw or None


def get_brain_class(google_sub: str | None = None) -> type:
    """agent.py 頂部 import；子行程執行時由 AGENT_DUNGEON_USER_SUB 注入使用者。"""
    sub = google_sub if google_sub is not None else runtime_google_sub()
    return make_brain_class(google_sub=sub)


def list_runtime_registry() -> tuple[str, ...]:
    return tuple(spec.module_id for spec in RUNTIME_REGISTRY)


# 供 agent.py 模板使用：Brain = get_brain_class()
Brain = get_brain_class()
