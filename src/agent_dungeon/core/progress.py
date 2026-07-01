from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

import yaml

from agent_dungeon.core.cloud_paths import APP_ROOT, paths_for_user
from agent_dungeon.forge.challenges import (
    BRAIN_FORGE_CHALLENGE_IDS,
    LOOP_FORGE_CHALLENGE_IDS,
    VOICE_FORGE_CHALLENGE_IDS,
)

QUESTS_PATH = APP_ROOT / "quests" / "quests.yaml"

MODULE_IDS = (
    "voice",
    "brain",
    "loop",
    "identity",
    "memory",
    "tools",
    "planning",
    "team",
)


class ModuleStatus(StrEnum):
    LOCKED = "locked"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


FORGE_CHALLENGE_IDS = VOICE_FORGE_CHALLENGE_IDS

VOICE_LEVEL_ID = "1"
BRAIN_LEVEL_ID = "2"
LOOP_LEVEL_ID = "3"
IDENTITY_LEVEL_ID = "4"
MEMORY_LEVEL_ID = "5"
TOOLS_LEVEL_ID = "6"
PLANNING_LEVEL_ID = "7"
TEAM_LEVEL_ID = "8"

CHALLENGE_XP = 33
XP_PER_LEVEL = 100


def forge_challenge_ids_for_level(level_id: str) -> tuple[str, ...]:
    if level_id == BRAIN_LEVEL_ID:
        return BRAIN_FORGE_CHALLENGE_IDS
    if level_id == LOOP_LEVEL_ID:
        return LOOP_FORGE_CHALLENGE_IDS
    return VOICE_FORGE_CHALLENGE_IDS


def load_quests_config() -> dict:
    if not QUESTS_PATH.is_file():
        return {"quests": []}
    raw = yaml.safe_load(QUESTS_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {"quests": []}
    quests = raw.get("quests")
    if not isinstance(quests, list):
        return {"quests": []}
    return {"quests": quests}


def get_quest(level_id: str) -> dict | None:
    for quest in load_quests_config().get("quests", []):
        if isinstance(quest, dict) and str(quest.get("id")) == level_id:
            return quest
    return None


def quest_subtitle(level_id: str) -> str:
    quest = get_quest(level_id)
    if quest is None:
        return ""
    subtitle = quest.get("subtitle")
    return str(subtitle).strip() if subtitle else ""


def quest_tag(level_id: str) -> str | None:
    quest = get_quest(level_id)
    if quest is None:
        return None
    tag = quest.get("tag")
    if not tag:
        return None
    text = str(tag).strip()
    return text or None


_FALLBACK_QUEST_HINTS: tuple[str, ...] = (
    "讓你的 Agent 說出第一句話！（第 1 關）",
    "替 Agent 裝上大腦（第 2 關）",
    "替 Agent 建立對話迴圈（第 3 關）",
    "建立 Agent 身份（第 4 關）",
    "替 Agent 裝上記憶（第 5 關）",
    "裝備 Agent 工具（第 6 關）",
    "教 Agent 規劃（第 7 關）",
    "組建 Agent 團隊（第 8 關）",
)


def _build_agent_next_quest_hints() -> tuple[str, ...]:
    hints: list[str] = []
    for quest in load_quests_config().get("quests", []):
        if not isinstance(quest, dict):
            continue
        level_id = str(quest.get("id") or "").strip()
        subtitle = str(quest.get("subtitle") or "").strip()
        if level_id and subtitle:
            hints.append(f"{subtitle}（第 {level_id} 關）")
    return tuple(hints) if hints else _FALLBACK_QUEST_HINTS


# 左欄 Agent 等級 0-based；index = 目前等級，值 = 下一「關」任務描述
AGENT_NEXT_QUEST_HINTS: tuple[str, ...] = _build_agent_next_quest_hints()


@dataclass
class LevelProgress:
    forge_lab_complete: bool = False
    mission_complete: bool = False
    forge_challenges: dict[str, bool] = field(default_factory=dict)


@dataclass
class DungeonProgress:
    xp: int = 0
    mp: int = 0
    xp_to_next: int = XP_PER_LEVEL
    rank_title: str = "Lv. 0"
    next_rank_hint: str = AGENT_NEXT_QUEST_HINTS[0]
    modules: dict[str, ModuleStatus] = field(default_factory=dict)
    levels: dict[str, LevelProgress] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.modules:
            self.modules = {module_id: ModuleStatus.LOCKED for module_id in MODULE_IDS}
            self.modules["voice"] = ModuleStatus.IN_PROGRESS
        if VOICE_LEVEL_ID not in self.levels:
            self.levels[VOICE_LEVEL_ID] = LevelProgress()


def _parse_module_status(value: object) -> ModuleStatus:
    if isinstance(value, str):
        try:
            return ModuleStatus(value)
        except ValueError:
            pass
    return ModuleStatus.LOCKED


def _progress_from_dict(raw: dict) -> DungeonProgress:
    modules_raw = raw.get("modules")
    modules: dict[str, ModuleStatus] = {mid: ModuleStatus.LOCKED for mid in MODULE_IDS}
    if isinstance(modules_raw, dict):
        for key, value in modules_raw.items():
            if key in MODULE_IDS:
                modules[key] = _parse_module_status(value)

    levels: dict[str, LevelProgress] = {}
    levels_raw = raw.get("levels")
    if isinstance(levels_raw, dict):
        for key, value in levels_raw.items():
            if isinstance(value, dict):
                level_id = str(key)
                challenge_ids = forge_challenge_ids_for_level(level_id)
                challenges_raw = value.get("forge_challenges")
                challenges: dict[str, bool] = {}
                if isinstance(challenges_raw, dict):
                    for cid in challenge_ids:
                        if cid in challenges_raw:
                            challenges[cid] = bool(challenges_raw[cid])
                    for cid, done in challenges_raw.items():
                        if cid not in challenges and isinstance(cid, str):
                            challenges[cid] = bool(done)
                levels[level_id] = LevelProgress(
                    forge_lab_complete=bool(value.get("forge_lab_complete")),
                    mission_complete=bool(value.get("mission_complete")),
                    forge_challenges=challenges,
                )

    progress = DungeonProgress(
        xp=int(raw.get("xp", 0) or 0),
        mp=int(raw.get("mp", 0) or 0),
        xp_to_next=int(raw.get("xp_to_next", XP_PER_LEVEL) or XP_PER_LEVEL),
        rank_title=str(raw.get("rank_title") or "Lv. 0"),
        next_rank_hint=str(raw.get("next_rank_hint") or AGENT_NEXT_QUEST_HINTS[0]),
        modules=modules,
        levels=levels,
    )
    if "voice" not in modules or modules["voice"] == ModuleStatus.LOCKED:
        progress.modules["voice"] = ModuleStatus.IN_PROGRESS
    progress.levels.pop("0", None)
    if VOICE_LEVEL_ID not in progress.levels:
        progress.levels[VOICE_LEVEL_ID] = LevelProgress()
    _sync_progress_derived_fields(progress)
    return progress


def _progress_to_dict(progress: DungeonProgress) -> dict:
    levels_payload: dict[str, dict] = {}
    for key, level in progress.levels.items():
        challenge_ids = forge_challenge_ids_for_level(key)
        levels_payload[key] = {
            "forge_lab_complete": level.forge_lab_complete,
            "mission_complete": level.mission_complete,
            "forge_challenges": {
                cid: level.forge_challenges.get(cid, False)
                for cid in challenge_ids
            },
        }
        for cid, done in level.forge_challenges.items():
            if cid not in levels_payload[key]["forge_challenges"]:
                levels_payload[key]["forge_challenges"][cid] = done

    return {
        "xp": progress.xp,
        "mp": progress.mp,
        "xp_to_next": progress.xp_to_next,
        "rank_title": progress.rank_title,
        "next_rank_hint": progress.next_rank_hint,
        "modules": {key: status.value for key, status in progress.modules.items()},
        "levels": levels_payload,
    }


def load_user_progress(google_sub: str) -> DungeonProgress:
    path = paths_for_user(google_sub).progress
    if not path.is_file():
        return DungeonProgress()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DungeonProgress()
    if not isinstance(raw, dict):
        return DungeonProgress()
    return _progress_from_dict(raw)


def save_user_progress(google_sub: str, progress: DungeonProgress) -> None:
    _sync_progress_derived_fields(progress)
    path = paths_for_user(google_sub).progress
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_progress_to_dict(progress), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def agent_level(progress: DungeonProgress) -> int:
    return sum(1 for status in progress.modules.values() if status == ModuleStatus.COMPLETE)


def next_rank_hint_for(progress: DungeonProgress) -> str:
    level = agent_level(progress)
    if level >= len(AGENT_NEXT_QUEST_HINTS):
        return "已達最高等級"
    return AGENT_NEXT_QUEST_HINTS[level]


def _level_xp(progress: DungeonProgress, level_id: str) -> int:
    level = progress.levels.get(level_id)
    if level is None:
        return 0
    challenge_ids = forge_challenge_ids_for_level(level_id)
    done = sum(1 for cid in challenge_ids if level.forge_challenges.get(cid, False))
    max_xp = XP_PER_LEVEL - 1
    per_challenge = max_xp // max(len(challenge_ids), 1)
    return min(done * per_challenge, max_xp)


def _voice_level_xp(progress: DungeonProgress) -> int:
    return _level_xp(progress, VOICE_LEVEL_ID)


def _brain_level_xp(progress: DungeonProgress) -> int:
    return _level_xp(progress, BRAIN_LEVEL_ID)


def _loop_level_xp(progress: DungeonProgress) -> int:
    return _level_xp(progress, LOOP_LEVEL_ID)


def agent_level_view(progress: DungeonProgress) -> tuple[int, str, int, int]:
    level = agent_level(progress)
    if level == 0:
        xp = _voice_level_xp(progress)
    elif level == 1:
        xp = _brain_level_xp(progress)
    elif level == 2:
        xp = _loop_level_xp(progress)
    else:
        xp = progress.xp
    xp_to_next = progress.xp_to_next or XP_PER_LEVEL
    return level, next_rank_hint_for(progress), xp, xp_to_next


def _sync_progress_derived_fields(progress: DungeonProgress) -> None:
    level = agent_level(progress)
    if progress.modules.get("voice") == ModuleStatus.COMPLETE:
        if progress.modules.get("brain") == ModuleStatus.LOCKED:
            progress.modules["brain"] = ModuleStatus.IN_PROGRESS
    if progress.modules.get("brain") == ModuleStatus.COMPLETE:
        if progress.modules.get("loop") == ModuleStatus.LOCKED:
            progress.modules["loop"] = ModuleStatus.IN_PROGRESS
        # 舊版進度：Brain 通關後解鎖 memory → 改為 loop
        if progress.modules.get("memory") == ModuleStatus.IN_PROGRESS:
            progress.modules["memory"] = ModuleStatus.LOCKED
            if progress.modules.get("loop") == ModuleStatus.LOCKED:
                progress.modules["loop"] = ModuleStatus.IN_PROGRESS
    if progress.modules.get("loop") == ModuleStatus.COMPLETE:
        if progress.modules.get("identity") == ModuleStatus.LOCKED:
            progress.modules["identity"] = ModuleStatus.IN_PROGRESS
    progress.rank_title = f"Lv. {level}"
    progress.next_rank_hint = next_rank_hint_for(progress)
    if level == 0:
        progress.xp = _voice_level_xp(progress)
    elif level == 1:
        progress.xp = _brain_level_xp(progress)
    elif level == 2:
        progress.xp = _loop_level_xp(progress)


def _level_progress(progress: DungeonProgress, level_id: str) -> LevelProgress | None:
    return progress.levels.get(level_id)


def challenge_complete(
    progress: DungeonProgress,
    challenge_id: str,
    *,
    level_id: str = VOICE_LEVEL_ID,
) -> bool:
    level = _level_progress(progress, level_id)
    if level is None:
        return False
    return level.forge_challenges.get(challenge_id, False)


def skill_forge_complete(
    progress: DungeonProgress,
    *,
    level_id: str = VOICE_LEVEL_ID,
) -> bool:
    level = _level_progress(progress, level_id)
    if level is None:
        return False
    challenge_ids = forge_challenge_ids_for_level(level_id)
    return all(level.forge_challenges.get(cid, False) for cid in challenge_ids)


def mark_forge_challenge_complete(
    progress: DungeonProgress,
    challenge_id: str,
    *,
    level_id: str = VOICE_LEVEL_ID,
) -> DungeonProgress:
    challenge_ids = forge_challenge_ids_for_level(level_id)
    if challenge_id not in challenge_ids:
        return progress

    if level_id == VOICE_LEVEL_ID:
        if agent_level(progress) > 0:
            return progress
    elif level_id == BRAIN_LEVEL_ID:
        if progress.modules.get("voice") != ModuleStatus.COMPLETE:
            return progress
        if agent_level(progress) > 1:
            return progress
    elif level_id == LOOP_LEVEL_ID:
        if progress.modules.get("brain") != ModuleStatus.COMPLETE:
            return progress
        if agent_level(progress) > 2:
            return progress
    else:
        return progress

    level = progress.levels.setdefault(level_id, LevelProgress())
    if level.forge_challenges.get(challenge_id, False):
        return progress
    level.forge_challenges[challenge_id] = True
    if level_id == VOICE_LEVEL_ID:
        progress.xp = _voice_level_xp(progress)
    elif level_id == BRAIN_LEVEL_ID:
        progress.xp = _brain_level_xp(progress)
    elif level_id == LOOP_LEVEL_ID:
        progress.xp = _loop_level_xp(progress)
    return progress


def mark_forge_lab_complete(progress: DungeonProgress) -> DungeonProgress:
    level = progress.levels.setdefault(VOICE_LEVEL_ID, LevelProgress())
    level.forge_lab_complete = True
    level.mission_complete = True
    progress.modules["voice"] = ModuleStatus.COMPLETE
    progress.modules["brain"] = ModuleStatus.IN_PROGRESS
    progress.xp = 0
    progress.mp += 1
    _sync_progress_derived_fields(progress)
    return progress


def mark_brain_forge_lab_complete(progress: DungeonProgress) -> DungeonProgress:
    level = progress.levels.setdefault(BRAIN_LEVEL_ID, LevelProgress())
    level.forge_lab_complete = True
    level.mission_complete = True
    progress.modules["brain"] = ModuleStatus.COMPLETE
    progress.modules["loop"] = ModuleStatus.IN_PROGRESS
    progress.xp = 0
    progress.mp += 1
    _sync_progress_derived_fields(progress)
    return progress


def mark_loop_forge_lab_complete(progress: DungeonProgress) -> DungeonProgress:
    level = progress.levels.setdefault(LOOP_LEVEL_ID, LevelProgress())
    level.forge_lab_complete = True
    level.mission_complete = True
    progress.modules["loop"] = ModuleStatus.COMPLETE
    progress.modules["identity"] = ModuleStatus.IN_PROGRESS
    progress.xp = 0
    progress.mp += 1
    _sync_progress_derived_fields(progress)
    return progress


def voice_module_online(progress: DungeonProgress) -> bool:
    level = progress.levels.get(VOICE_LEVEL_ID)
    if level is None:
        return False
    return level.forge_lab_complete or progress.modules.get("voice") == ModuleStatus.COMPLETE


def brain_module_online(progress: DungeonProgress) -> bool:
    level = progress.levels.get(BRAIN_LEVEL_ID)
    if level is None:
        return False
    return level.forge_lab_complete or progress.modules.get("brain") == ModuleStatus.COMPLETE


def loop_module_online(progress: DungeonProgress) -> bool:
    level = progress.levels.get(LOOP_LEVEL_ID)
    if level is None:
        return False
    return level.forge_lab_complete or progress.modules.get("loop") == ModuleStatus.COMPLETE
