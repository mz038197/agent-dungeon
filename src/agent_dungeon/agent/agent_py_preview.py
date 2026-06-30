from __future__ import annotations

from agent_dungeon.forge.challenges import BRAIN_FORGE_CHALLENGES, VOICE_FORGE_CHALLENGES
from agent_dungeon.core.progress import (
    BRAIN_LEVEL_ID,
    DungeonProgress,
    ModuleStatus,
    brain_module_online,
    challenge_complete,
    voice_module_online,
)

_PREVIEW_HEADER = "# agent.py — 建造中"
_VOICE_SECTION = "# === Voice 模組 ==="
_BRAIN_SECTION = "# === Brain 模組 ==="
_BRAIN_LOCKED = "# 🔒 尚未解鎖"
_VOICE_LOCKED = "# 🔒 完成 Skill Forge 解鎖"
_BRAIN_FORGE_LOCKED = "# 🔒 完成 Skill Forge 解鎖"


def _default_voice_codes() -> dict[str, str]:
    return {challenge.id: challenge.default_code for challenge in VOICE_FORGE_CHALLENGES}


def _default_brain_codes() -> dict[str, str]:
    return {challenge.id: challenge.default_code for challenge in BRAIN_FORGE_CHALLENGES}


def _code_for_challenge(
    challenge_id: str,
    challenge_codes: dict[str, str],
    *,
    defaults: dict[str, str],
) -> str:
    raw = challenge_codes.get(challenge_id, defaults.get(challenge_id, ""))
    return str(raw).strip() or defaults.get(challenge_id, "")


def _voice_section(
    progress: DungeonProgress,
    *,
    challenge_codes: dict[str, str],
    lab_code: str,
) -> list[str]:
    codes = challenge_codes or {}
    defaults = _default_voice_codes()
    if voice_module_online(progress):
        body = lab_code.strip() or _code_for_challenge("c3", codes, defaults=defaults)
        return [_VOICE_SECTION, body]
    if challenge_complete(progress, "c3"):
        return [_VOICE_SECTION, _code_for_challenge("c3", codes, defaults=defaults)]
    if challenge_complete(progress, "c2"):
        return [_VOICE_SECTION, _code_for_challenge("c2", codes, defaults=defaults)]
    if challenge_complete(progress, "c1"):
        return [_VOICE_SECTION, _code_for_challenge("c1", codes, defaults=defaults)]
    return [_VOICE_SECTION, _VOICE_LOCKED]


def _brain_section(
    progress: DungeonProgress,
    *,
    brain_challenge_codes: dict[str, str],
    brain_lab_code: str,
) -> list[str]:
    if progress.modules.get("voice") != ModuleStatus.COMPLETE:
        return [_BRAIN_SECTION, _BRAIN_LOCKED]

    codes = brain_challenge_codes or {}
    defaults = _default_brain_codes()
    if brain_module_online(progress):
        body = brain_lab_code.strip() or _code_for_challenge("c3", codes, defaults=defaults)
        return [_BRAIN_SECTION, body]
    for cid in ("c3", "c2", "c1"):
        if challenge_complete(progress, cid, level_id=BRAIN_LEVEL_ID):
            return [_BRAIN_SECTION, _code_for_challenge(cid, codes, defaults=defaults)]
    return [_BRAIN_SECTION, _BRAIN_FORGE_LOCKED]


def build_agent_py_preview(
    progress: DungeonProgress,
    *,
    challenge_codes: dict[str, str] | None = None,
    lab_code: str = "",
    brain_challenge_codes: dict[str, str] | None = None,
    brain_lab_code: str = "",
) -> str:
    lines = [_PREVIEW_HEADER, ""]
    lines.extend(
        _voice_section(
            progress,
            challenge_codes=challenge_codes or {},
            lab_code=lab_code,
        )
    )
    lines.append("")
    lines.extend(
        _brain_section(
            progress,
            brain_challenge_codes=brain_challenge_codes or {},
            brain_lab_code=brain_lab_code,
        )
    )
    lines.append("")
    return "\n".join(lines)
