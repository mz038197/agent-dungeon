from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

import yaml

from agent_dungeon.core.cloud_paths import APP_ROOT, paths_for_user

QUESTS_PATH = APP_ROOT / "quests" / "quests.yaml"

MODULE_IDS = (
    "voice",
    "brain",
    "memory",
    "identity",
    "tools",
    "planning",
    "team",
)


class ModuleStatus(StrEnum):
    LOCKED = "locked"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


FORGE_CHALLENGE_IDS = ("c1", "c2", "c3")

VOICE_LEVEL_ID = "1"

CHALLENGE_XP = 33
XP_PER_LEVEL = 100


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
    "替 Agent 裝上記憶（第 3 關）",
    "建立 Agent 身份（第 4 關）",
    "裝備 Agent 工具（第 5 關）",
    "教 Agent 規劃（第 6 關）",
    "組建 Agent 團隊（第 7 關）",
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
                challenges_raw = value.get("forge_challenges")
                challenges: dict[str, bool] = {}
                if isinstance(challenges_raw, dict):
                    for cid in FORGE_CHALLENGE_IDS:
                        if cid in challenges_raw:
                            challenges[cid] = bool(challenges_raw[cid])
                levels[str(key)] = LevelProgress(
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
    return {
        "xp": progress.xp,
        "mp": progress.mp,
        "xp_to_next": progress.xp_to_next,
        "rank_title": progress.rank_title,
        "next_rank_hint": progress.next_rank_hint,
        "modules": {key: status.value for key, status in progress.modules.items()},
        "levels": {
            key: {
                "forge_lab_complete": level.forge_lab_complete,
                "mission_complete": level.mission_complete,
                "forge_challenges": {
                    cid: level.forge_challenges.get(cid, False)
                    for cid in FORGE_CHALLENGE_IDS
                },
            }
            for key, level in progress.levels.items()
        },
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


def _voice_level_xp(progress: DungeonProgress) -> int:
    level = progress.levels.get(VOICE_LEVEL_ID)
    if level is None:
        return 0
    done = sum(
        1 for cid in FORGE_CHALLENGE_IDS if level.forge_challenges.get(cid, False)
    )
    return min(done * CHALLENGE_XP, XP_PER_LEVEL - 1)


def agent_level_view(progress: DungeonProgress) -> tuple[int, str, int, int]:
    level = agent_level(progress)
    xp = _voice_level_xp(progress) if level == 0 else progress.xp
    xp_to_next = progress.xp_to_next or XP_PER_LEVEL
    return level, next_rank_hint_for(progress), xp, xp_to_next


def _sync_progress_derived_fields(progress: DungeonProgress) -> None:
    level = agent_level(progress)
    if progress.modules.get("voice") == ModuleStatus.COMPLETE:
        if progress.modules.get("brain") == ModuleStatus.LOCKED:
            progress.modules["brain"] = ModuleStatus.IN_PROGRESS
    progress.rank_title = f"Lv. {level}"
    progress.next_rank_hint = next_rank_hint_for(progress)
    if level == 0:
        progress.xp = _voice_level_xp(progress)


def challenge_complete(progress: DungeonProgress, challenge_id: str) -> bool:
    level = progress.levels.get(VOICE_LEVEL_ID)
    if level is None:
        return False
    return level.forge_challenges.get(challenge_id, False)


def skill_forge_complete(progress: DungeonProgress) -> bool:
    level = progress.levels.get(VOICE_LEVEL_ID)
    if level is None:
        return False
    return all(level.forge_challenges.get(cid, False) for cid in FORGE_CHALLENGE_IDS)


def mark_forge_challenge_complete(
    progress: DungeonProgress,
    challenge_id: str,
) -> DungeonProgress:
    if challenge_id not in FORGE_CHALLENGE_IDS:
        return progress
    if agent_level(progress) > 0:
        return progress
    level = progress.levels.setdefault(VOICE_LEVEL_ID, LevelProgress())
    if level.forge_challenges.get(challenge_id, False):
        return progress
    level.forge_challenges[challenge_id] = True
    progress.xp = _voice_level_xp(progress)
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


def voice_module_online(progress: DungeonProgress) -> bool:
    level = progress.levels.get(VOICE_LEVEL_ID)
    if level is None:
        return False
    return level.forge_lab_complete or progress.modules.get("voice") == ModuleStatus.COMPLETE
