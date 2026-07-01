from __future__ import annotations

from pathlib import Path

from agent_dungeon.core.progress import (
    DungeonProgress,
    ModuleStatus,
    brain_module_online,
    voice_module_online,
)
from agent_dungeon.forge.agent_py_store import normalize_to_main_function
from agent_dungeon.forge.challenges import (
    brain_challenge_codes_from_stored,
    challenge_codes_from_stored,
    loop_challenge_codes_from_stored,
)

_PREVIEW_HEADER = "# agent.py — 建造中"


def _normalize_preview_main(body: str) -> str:
    raw = body.strip()
    if not raw:
        return "def main():\n    pass"
    if "def main" in raw:
        return raw
    indented = "\n".join(f"    {line}" if line.strip() else "" for line in raw.splitlines())
    return f"def main():\n{indented}"


def _best_main_body(
    progress: DungeonProgress,
    *,
    challenge_codes: dict[str, str],
    lab_code: str,
    brain_challenge_codes: dict[str, str],
    brain_lab_code: str,
    loop_challenge_codes: dict[str, str] | None = None,
    loop_lab_code: str = "",
) -> str:
    if progress.modules.get("loop") == ModuleStatus.COMPLETE or loop_lab_code.strip():
        if loop_lab_code.strip():
            return loop_lab_code.strip()
        if loop_challenge_codes:
            for cid in ("c4", "c3", "c2", "c1"):
                raw = loop_challenge_codes.get(cid, "").strip()
                if raw:
                    return raw

    if brain_module_online(progress):
        if brain_lab_code.strip():
            return brain_lab_code.strip()
        for cid in ("c3", "c2", "c1"):
            raw = brain_challenge_codes.get(cid, "").strip()
            if raw:
                return raw

    if voice_module_online(progress):
        for cid in ("c3", "c2", "c1"):
            raw = challenge_codes.get(cid, "").strip()
            if raw:
                return raw

    if progress.modules.get("brain") != ModuleStatus.LOCKED:
        for cid in ("c3", "c2", "c1"):
            raw = brain_challenge_codes.get(cid, "").strip()
            if raw:
                return raw

    for cid in ("c3", "c2", "c1"):
        raw = challenge_codes.get(cid, "").strip()
        if raw:
            return _normalize_preview_main(raw)

    return "def main():\n    pass"


def build_agent_py_preview(
    progress: DungeonProgress,
    *,
    challenge_codes: dict[str, str] | None = None,
    lab_code: str = "",
    brain_challenge_codes: dict[str, str] | None = None,
    brain_lab_code: str = "",
    loop_challenge_codes: dict[str, str] | None = None,
    loop_lab_code: str = "",
    agent_py_path: str | None = None,
) -> str:
    if agent_py_path:
        path = Path(agent_py_path)
        if path.is_file():
            return path.read_text(encoding="utf-8")

    voice_codes = challenge_codes or challenge_codes_from_stored(None)
    brain_codes = brain_challenge_codes or brain_challenge_codes_from_stored(None)
    loop_codes = loop_challenge_codes or loop_challenge_codes_from_stored(None)

    main_body = normalize_to_main_function(
        _best_main_body(
            progress,
            challenge_codes=voice_codes,
            lab_code=lab_code,
            brain_challenge_codes=brain_codes,
            brain_lab_code=brain_lab_code,
            loop_challenge_codes=loop_codes,
            loop_lab_code=loop_lab_code,
        )
    )

    return "\n".join(
        [
            _PREVIEW_HEADER,
            "",
            main_body,
            "",
            'if __name__ == "__main__":',
            "    main()",
        ]
    )
