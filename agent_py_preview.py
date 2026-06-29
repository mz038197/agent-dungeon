from __future__ import annotations

from forge_challenges import VOICE_FORGE_CHALLENGES
from progress import DungeonProgress, challenge_complete, voice_module_online

_PREVIEW_HEADER = "# agent.py — 建造中"
_VOICE_SECTION = "# === Voice 模組 ==="
_BRAIN_SECTION = "# === Brain 模組 ==="
_BRAIN_LOCKED = "# 🔒 尚未解鎖"
_VOICE_LOCKED = "# 🔒 完成 Skill Forge 解鎖"


def _default_codes() -> dict[str, str]:
    return {challenge.id: challenge.default_code for challenge in VOICE_FORGE_CHALLENGES}


def _code_for_challenge(challenge_id: str, challenge_codes: dict[str, str]) -> str:
    defaults = _default_codes()
    raw = challenge_codes.get(challenge_id, defaults.get(challenge_id, ""))
    return str(raw).strip() or defaults.get(challenge_id, "")


def build_agent_py_preview(
    progress: DungeonProgress,
    *,
    challenge_codes: dict[str, str] | None = None,
    lab_code: str = "",
) -> str:
    codes = challenge_codes or {}
    lines = [_PREVIEW_HEADER, ""]

    if voice_module_online(progress):
        body = lab_code.strip() or _code_for_challenge("c3", codes)
        lines.extend([_VOICE_SECTION, body])
    elif challenge_complete(progress, "c3"):
        lines.extend([_VOICE_SECTION, _code_for_challenge("c3", codes)])
    elif challenge_complete(progress, "c2"):
        lines.extend([_VOICE_SECTION, _code_for_challenge("c2", codes)])
    elif challenge_complete(progress, "c1"):
        lines.extend([_VOICE_SECTION, _code_for_challenge("c1", codes)])
    else:
        lines.extend([_VOICE_SECTION, _VOICE_LOCKED])

    lines.extend(["", _BRAIN_SECTION, _BRAIN_LOCKED, ""])
    return "\n".join(lines)
