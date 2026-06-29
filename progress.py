from __future__ import annotations

import yaml
from pathlib import Path

QUESTS_PATH = Path(__file__).resolve().parent / "quests" / "quests.yaml"


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
