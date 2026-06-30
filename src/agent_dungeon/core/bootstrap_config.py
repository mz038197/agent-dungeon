from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from openai_tts.settings import MAX_TTS_SPEED, MIN_TTS_SPEED, Settings

from agent_dungeon.core.cloud_paths import (
    paths_for_user,
    peas_agent_home,
    shared_config_path,
    shared_tts_config_path,
)

DEFAULT_TTS_BASE_URL = "https://ai.vanscoding.com/v1"
DEFAULT_TTS_MODEL = "openai@gpt-4o-mini-tts"
LEGACY_HARDCODED_TTS_INSTRUCTIONS = "用台灣繁體中文說話。"
LEGACY_HARDCODED_TTS_SPEED = 1.0
TTS_VOICE_OPTIONS = frozenset(
    {
        "alloy",
        "ash",
        "ballad",
        "coral",
        "echo",
        "fable",
        "nova",
        "onyx",
        "sage",
        "shimmer",
    }
)


def _default_config() -> dict[str, Any]:
    return {
        "workspace": str(peas_agent_home() / "_unused_workspace"),
        "token_budget": 100000,
        "llm": {
            "api_key": "",
            "model": os.environ.get("PEAS_LLM_MODEL", "gpt-5.4-mini"),
            "temperature": 0.2,
            "base_url": os.environ.get("PEAS_LLM_BASE_URL", "https://api.openai.com/v1"),
            "use_responses_api": True,
            "output_version": "responses/v1",
            "reasoning": {"effort": "medium", "summary": "auto"},
        },
    }


def default_tts_config() -> dict[str, Any]:
    env = Settings()
    api_key = os.environ.get("PEAS_TTS_API_KEY", "").strip()
    base_url = os.environ.get("PEAS_TTS_BASE_URL", "").strip() or DEFAULT_TTS_BASE_URL
    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": DEFAULT_TTS_MODEL,
        "enabled": False,
        "voice": env.voice,
        "instructions": env.instructions,
        "speed": env.speed,
    }


def _deep_merge_dict(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def _merge_env_into_config(config: dict[str, Any]) -> dict[str, Any]:
    defaults = _default_config()
    merged = _deep_merge_dict(defaults, config)
    llm = dict(merged.get("llm") or {})
    api_key = os.environ.get("PEAS_LLM_API_KEY", "").strip()
    if api_key:
        llm["api_key"] = api_key
    model = os.environ.get("PEAS_LLM_MODEL", "").strip()
    if model:
        llm["model"] = model
    base_url = os.environ.get("PEAS_LLM_BASE_URL", "").strip()
    if base_url:
        llm["base_url"] = base_url
    merged["llm"] = llm
    return merged


def _is_legacy_hardcoded_tts_config(config: dict[str, Any]) -> bool:
    try:
        speed = float(config.get("speed", 0))
    except (TypeError, ValueError):
        return False
    return (
        speed == LEGACY_HARDCODED_TTS_SPEED
        and str(config.get("instructions", "")) == LEGACY_HARDCODED_TTS_INSTRUCTIONS
    )


def _upgrade_legacy_hardcoded_tts_config(config: dict[str, Any]) -> dict[str, Any]:
    defaults = default_tts_config()
    upgraded = dict(config)
    upgraded["instructions"] = defaults["instructions"]
    upgraded["speed"] = defaults["speed"]
    if str(upgraded.get("voice", "")) not in TTS_VOICE_OPTIONS:
        upgraded["voice"] = defaults["voice"]
    return upgraded


def normalize_tts_config(
    raw: dict[str, Any],
    defaults: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = defaults or default_tts_config()
    voice = str(raw.get("voice", raw.get("tts_voice", base["voice"])))
    if voice not in TTS_VOICE_OPTIONS:
        voice = str(base["voice"])

    try:
        speed = float(raw.get("speed", raw.get("tts_speed", base["speed"])))
    except (TypeError, ValueError):
        speed = float(base["speed"])
    speed = max(MIN_TTS_SPEED, min(MAX_TTS_SPEED, speed))

    enabled = raw.get("enabled", raw.get("tts_enabled", base["enabled"]))
    instructions = raw.get("instructions", raw.get("tts_instructions", base["instructions"]))
    instructions = str(instructions).strip() or str(base["instructions"])
    base_url = str(raw.get("base_url", base["base_url"])).strip() or str(base["base_url"])
    model = str(raw.get("model", base["model"])).strip() or str(base["model"])
    api_key = str(raw.get("api_key", base["api_key"]))
    env_api_key = os.environ.get("PEAS_TTS_API_KEY", "").strip()
    if env_api_key:
        api_key = env_api_key

    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
        "enabled": bool(enabled),
        "voice": voice,
        "instructions": instructions,
        "speed": speed,
    }


def read_tts_config(path: Path) -> tuple[dict[str, Any], bool]:
    defaults = default_tts_config()
    if not path.is_file():
        return defaults, True

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return defaults, True

    if not isinstance(raw, dict):
        return defaults, True

    normalized = normalize_tts_config(raw, defaults)
    if _is_legacy_hardcoded_tts_config(normalized):
        normalized = normalize_tts_config(
            _upgrade_legacy_hardcoded_tts_config(normalized),
            defaults,
        )
        return normalized, True
    return normalized, raw != normalized


def save_tts_config(path: Path, settings: dict[str, Any]) -> str | None:
    payload = normalize_tts_config(settings)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        return f"無法寫入語音設定檔：{exc}"
    return None


def ensure_tts_config_file(path: Path) -> str | None:
    prefs, needs_repair = read_tts_config(path)
    if not needs_repair:
        return None
    return save_tts_config(path, prefs)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def default_preferences() -> dict[str, Any]:
    return {"llm": {"reasoning": {"effort": "medium", "summary": "auto"}}}


def _read_json_dict(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _load_shared_config_dict() -> dict[str, Any]:
    raw = _read_json_dict(shared_config_path())
    return _merge_env_into_config(_deep_merge_dict(_default_config(), raw))


def build_effective_config(google_sub: str) -> dict[str, Any]:
    base = _load_shared_config_dict()
    paths = paths_for_user(google_sub)
    prefs = _read_json_dict(paths.preferences) or default_preferences()
    llm = dict(base.get("llm") or {})
    pref_llm = prefs.get("llm")
    if isinstance(pref_llm, dict):
        pref_reasoning = pref_llm.get("reasoning")
        if isinstance(pref_reasoning, dict):
            reasoning = dict(llm.get("reasoning") or {})
            reasoning.update(pref_reasoning)
            llm["reasoning"] = reasoning
    base["llm"] = llm
    return base


def write_effective_config(google_sub: str) -> None:
    paths = paths_for_user(google_sub)
    _write_json(paths.effective_config, build_effective_config(google_sub))


def ensure_user_agent_config(google_sub: str) -> None:
    paths = paths_for_user(google_sub)
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.workspace.mkdir(parents=True, exist_ok=True)

    if not paths.tts.is_file():
        shared_tts, _ = read_tts_config(shared_tts_config_path())
        save_tts_config(paths.tts, shared_tts)

    if not paths.preferences.is_file():
        prefs = default_preferences()
        shared = _read_json_dict(shared_config_path())
        shared_llm = shared.get("llm")
        if isinstance(shared_llm, dict):
            shared_reasoning = shared_llm.get("reasoning")
            if isinstance(shared_reasoning, dict):
                reasoning = dict(prefs["llm"]["reasoning"])
                effort = shared_reasoning.get("effort")
                summary = shared_reasoning.get("summary")
                if effort is not None:
                    reasoning["effort"] = str(effort)
                if summary is not None:
                    reasoning["summary"] = str(summary)
                prefs["llm"]["reasoning"] = reasoning
        _write_json(paths.preferences, prefs)

    write_effective_config(google_sub)


def bootstrap_shared_config() -> None:
    home = peas_agent_home()
    home.mkdir(parents=True, exist_ok=True)

    config_path = shared_config_path()
    if config_path.is_file():
        try:
            existing = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}
    else:
        existing = {}
    if not isinstance(existing, dict):
        existing = {}
    merged = _merge_env_into_config(_deep_merge_dict(_default_config(), existing))
    _write_json(config_path, merged)

    ensure_tts_config_file(shared_tts_config_path())
