from __future__ import annotations

import json

import pytest

from agent_dungeon.core.bootstrap_config import (
    build_effective_config,
    ensure_user_agent_config,
    write_effective_config,
)
from agent_dungeon.core.cloud_paths import paths_for_user


@pytest.fixture
def peas_home(tmp_path, monkeypatch):
    home = tmp_path / "data"
    monkeypatch.setenv("PEAS_AGENT_HOME", str(home))
    monkeypatch.setenv("PEAS_LLM_API_KEY", "sk-env")
    return home


def test_two_users_get_isolated_preferences_and_effective_config(peas_home) -> None:
    shared_config = peas_home / "config.json"
    shared_config.parent.mkdir(parents=True, exist_ok=True)
    shared_config.write_text(
        json.dumps(
            {
                "llm": {
                    "reasoning": {"effort": "low", "summary": "auto"},
                    "use_responses_api": True,
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    shared_tts = peas_home / "tts.json"
    shared_tts.write_text(
        json.dumps({"enabled": True, "voice": "nova"}, ensure_ascii=False),
        encoding="utf-8",
    )

    ensure_user_agent_config("sub-a")
    ensure_user_agent_config("sub-b")

    paths_a = paths_for_user("sub-a")
    paths_b = paths_for_user("sub-b")
    assert paths_a.preferences != paths_b.preferences

    prefs_a = json.loads(paths_a.preferences.read_text(encoding="utf-8"))
    prefs_a["llm"]["reasoning"]["effort"] = "high"
    paths_a.preferences.write_text(json.dumps(prefs_a, ensure_ascii=False, indent=2), encoding="utf-8")
    write_effective_config("sub-a")

    prefs_b = json.loads(paths_b.preferences.read_text(encoding="utf-8"))
    assert prefs_b["llm"]["reasoning"]["effort"] == "low"

    effective_a = build_effective_config("sub-a")
    effective_b = build_effective_config("sub-b")
    assert effective_a["llm"]["reasoning"]["effort"] == "high"
    assert effective_b["llm"]["reasoning"]["effort"] == "low"
    assert effective_a["llm"]["api_key"] == "sk-env"
