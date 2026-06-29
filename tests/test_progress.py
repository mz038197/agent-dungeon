from __future__ import annotations

from progress import load_quests_config


def test_load_empty_quests() -> None:
    payload = load_quests_config()
    assert payload["quests"] == []
