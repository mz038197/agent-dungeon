from __future__ import annotations

from agent_dungeon.core.progress import (
    AGENT_NEXT_QUEST_HINTS,
    load_quests_config,
    quest_subtitle,
    quest_tag,
)


def test_load_quests_includes_all_seven_levels() -> None:
    payload = load_quests_config()
    assert len(payload["quests"]) == 7
    assert payload["quests"][0]["id"] == "1"
    assert payload["quests"][-1]["id"] == "7"


def test_quest_subtitle_level_one() -> None:
    assert quest_subtitle("1") == "讓你的 Agent 說出第一句話！"


def test_quest_tag_level_one() -> None:
    assert quest_tag("1") == "新手村起點"


def test_agent_next_quest_hints_from_yaml() -> None:
    assert len(AGENT_NEXT_QUEST_HINTS) == 7
    assert AGENT_NEXT_QUEST_HINTS[0] == "讓你的 Agent 說出第一句話！（第 1 關）"
    assert "第 7 關" in AGENT_NEXT_QUEST_HINTS[6]
