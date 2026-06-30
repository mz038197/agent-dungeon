from __future__ import annotations

from agent_dungeon.core.cloud_paths import page_data_path, paths_for_user
from agent_dungeon.core.progress import (
    BRAIN_LEVEL_ID,
    DungeonProgress,
    ModuleStatus,
    VOICE_LEVEL_ID,
    agent_level_view,
    brain_module_online,
    challenge_complete,
    skill_forge_complete,
    voice_module_online,
)
from agent_dungeon.ui.sidebar_nav import MODULE_DEFS, ModuleId


def _status_label(status: ModuleStatus) -> str:
    if status == ModuleStatus.IN_PROGRESS:
        return "進行中"
    if status == ModuleStatus.COMPLETE:
        return "已完成"
    return "未解鎖"


def build_left_sidebar_context(
    progress: DungeonProgress,
    *,
    current_module: ModuleId | None,
) -> dict[str, object]:
    module_summaries: list[str] = []
    for raw in MODULE_DEFS:
        module_id = str(raw["id"])
        status = progress.modules.get(module_id, ModuleStatus.LOCKED)
        module_summaries.append(f"{raw['label']}={_status_label(status)}")

    current_label = "（無）"
    if current_module is not None:
        for raw in MODULE_DEFS:
            if raw["id"] == current_module:
                current_label = str(raw["label"])
                break

    level, _, xp, xp_to_next = agent_level_view(progress)
    return {
        "左欄等級": f"Lv. {level}",
        "左欄XP": f"{xp}/{xp_to_next}",
        "左欄MP": progress.mp,
        "左欄目前模組": current_label,
        "左欄模組摘要": "；".join(module_summaries),
    }


def build_voice_forge_context(progress: DungeonProgress) -> dict[str, object]:
    forge_done = skill_forge_complete(progress, level_id=VOICE_LEVEL_ID)
    lab_done = voice_module_online(progress)
    return {
        "中欄SkillForge_C1": "完成" if challenge_complete(progress, "c1", level_id=VOICE_LEVEL_ID) else "進行中",
        "中欄SkillForge_C2": "完成" if challenge_complete(progress, "c2", level_id=VOICE_LEVEL_ID) else "進行中",
        "中欄SkillForge_C3": "完成" if challenge_complete(progress, "c3", level_id=VOICE_LEVEL_ID) else "進行中",
        "中欄SkillForge": "已完成" if forge_done else "進行中",
        "中欄ForgeLab": "已完成" if lab_done else ("已解鎖" if forge_done else "鎖定"),
        "中欄Voice模組": "Online" if lab_done else "Offline",
    }


def build_brain_forge_context(progress: DungeonProgress) -> dict[str, object]:
    forge_done = skill_forge_complete(progress, level_id=BRAIN_LEVEL_ID)
    lab_done = brain_module_online(progress)
    return {
        "中欄SkillForge_C1": "完成" if challenge_complete(progress, "c1", level_id=BRAIN_LEVEL_ID) else "進行中",
        "中欄SkillForge_C2": "完成" if challenge_complete(progress, "c2", level_id=BRAIN_LEVEL_ID) else "進行中",
        "中欄SkillForge_C3": "完成" if challenge_complete(progress, "c3", level_id=BRAIN_LEVEL_ID) else "進行中",
        "中欄SkillForge": "已完成" if forge_done else "進行中",
        "中欄ForgeLab": "已完成" if lab_done else ("已解鎖" if forge_done else "鎖定"),
        "中欄Brain模組": "Online" if lab_done else "Offline",
    }


def build_dungeon_extra_context(
    progress: DungeonProgress,
    *,
    page_name: str,
    google_sub: str | None,
    current_module: ModuleId | None = None,
    **page_fields: object,
) -> str:
    from agent_dungeon.ui.shell_ui import format_extra_context

    fields: dict[str, object] = {}
    fields.update(build_left_sidebar_context(progress, current_module=current_module))
    if page_name == "Voice":
        fields.update(build_voice_forge_context(progress))
    elif page_name == "Brain":
        fields.update(build_brain_forge_context(progress))
    fields.update(page_fields)
    if google_sub is not None:
        shared_path = page_data_path(page_name, paths_for_user(google_sub))
        fields["共享資料檔"] = shared_path.resolve().as_posix()
    return format_extra_context(page_name, **fields)
