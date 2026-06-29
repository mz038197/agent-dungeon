from __future__ import annotations

import json

import pytest

from bootstrap_config import (
    DEFAULT_TTS_BASE_URL,
    DEFAULT_TTS_MODEL,
    bootstrap_shared_config,
    default_tts_config,
    ensure_tts_config_file,
    normalize_tts_config,
    read_tts_config,
)


@pytest.fixture
def peas_home(tmp_path, monkeypatch):
    home = tmp_path / "data"
    monkeypatch.setenv("PEAS_AGENT_HOME", str(home))
    return home


def test_bootstrap_creates_tts_with_router_fields(peas_home) -> None:
    bootstrap_shared_config()
    tts_path = peas_home / "tts.json"
    payload = json.loads(tts_path.read_text(encoding="utf-8"))
    assert payload["base_url"] == DEFAULT_TTS_BASE_URL
    assert payload["model"] == DEFAULT_TTS_MODEL


def test_ensure_tts_merges_missing_router_fields(peas_home) -> None:
    tts_path = peas_home / "tts.json"
    tts_path.parent.mkdir(parents=True, exist_ok=True)
    tts_path.write_text(
        json.dumps(
            {
                "api_key": "vcr_sk_test",
                "enabled": True,
                "voice": "nova",
                "instructions": default_tts_config()["instructions"],
                "speed": 1.25,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert ensure_tts_config_file(tts_path) is None
    payload = json.loads(tts_path.read_text(encoding="utf-8"))
    assert payload["api_key"] == "vcr_sk_test"
    assert payload["enabled"] is True
    assert payload["base_url"] == DEFAULT_TTS_BASE_URL
    assert payload["model"] == DEFAULT_TTS_MODEL


def test_normalize_tts_empty_instructions_falls_back(peas_home) -> None:
    defaults = default_tts_config()
    normalized = normalize_tts_config({"instructions": "   "}, defaults)
    assert normalized["instructions"] == defaults["instructions"]


def test_bootstrap_deep_merges_llm_reasoning(peas_home, monkeypatch) -> None:
    monkeypatch.setenv("PEAS_LLM_API_KEY", "sk-env")
    config_path = peas_home / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                "llm": {
                    "api_key": "sk-disk",
                    "reasoning": {"effort": "high"},
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    bootstrap_shared_config()
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["llm"]["api_key"] == "sk-env"
    assert payload["llm"]["reasoning"]["effort"] == "high"
    assert payload["llm"]["reasoning"]["summary"] == "auto"
    assert payload["llm"]["use_responses_api"] is True


def test_read_tts_repairs_empty_file(peas_home) -> None:
    tts_path = peas_home / "tts.json"
    tts_path.parent.mkdir(parents=True, exist_ok=True)
    tts_path.write_text("", encoding="utf-8")

    prefs, needs_repair = read_tts_config(tts_path)
    assert needs_repair is True
    assert prefs["model"] == DEFAULT_TTS_MODEL
