from __future__ import annotations

import json
import sys
import types
from importlib import util
from pathlib import Path

import pytest

from agent_dungeon.auth.google_oauth import GoogleUserClaims
from agent_dungeon.core.cloud_paths import paths_for_user


def _load_agent_panel_module(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    fake_streamlit = types.ModuleType("streamlit")
    fake_streamlit.session_state = {}
    fake_streamlit_components = types.ModuleType("streamlit.components")
    fake_streamlit_components_v1 = types.ModuleType("streamlit.components.v1")
    fake_streamlit.components = fake_streamlit_components
    fake_streamlit_components.v1 = fake_streamlit_components_v1
    fake_openai_tts_settings = types.ModuleType("openai_tts.settings")
    fake_openai_tts_settings.MIN_TTS_SPEED = 0.25
    fake_openai_tts_settings.MAX_TTS_SPEED = 4.0
    fake_openai_tts_settings.Settings = lambda: types.SimpleNamespace(
        voice="nova",
        instructions="default instructions",
        speed=1.25,
    )
    fake_openai_tts = types.ModuleType("openai_tts")
    fake_openai_tts.Settings = fake_openai_tts_settings.Settings
    fake_openai_tts.stream_tts_play = lambda *_args, **_kwargs: None
    fake_openai_tts.settings = fake_openai_tts_settings

    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    fake_streamlit_components = types.ModuleType("streamlit.components")
    fake_streamlit_components_v1 = types.ModuleType("streamlit.components.v1")
    monkeypatch.setitem(sys.modules, "streamlit.components", fake_streamlit_components)
    monkeypatch.setitem(sys.modules, "streamlit.components.v1", fake_streamlit_components_v1)
    monkeypatch.setitem(sys.modules, "openai_tts", fake_openai_tts)
    monkeypatch.setitem(sys.modules, "openai_tts.settings", fake_openai_tts_settings)
    fake_multimodal = types.ModuleType("st_multimodal_chatinput")
    fake_multimodal.multimodal_chatinput = lambda **_kwargs: None
    monkeypatch.setitem(sys.modules, "st_multimodal_chatinput", fake_multimodal)

    module_path = Path(__file__).parents[1] / "src" / "agent_dungeon" / "agent" / "agent_panel.py"
    spec = util.spec_from_file_location("agent_panel_under_test", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = util.module_from_spec(spec)
    sys.modules["agent_panel_under_test"] = module
    spec.loader.exec_module(module)

    home = tmp_path / "data"
    monkeypatch.setenv("PEAS_AGENT_HOME", str(home))
    user_paths = paths_for_user("sub-test")
    fake_user = GoogleUserClaims(
        email="test@example.com",
        name="Test",
        google_sub="sub-test",
    )
    fake_streamlit.session_state = {}
    monkeypatch.setattr(
        module,
        "get_auth_user",
        lambda _session_state: fake_user,
    )
    module._init_panel_ctx(user_paths)
    return module, fake_streamlit, user_paths


def test_parse_history_entry_supports_legacy_two_tuple(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module, _, _ = _load_agent_panel_module(monkeypatch, tmp_path)
    assert module._parse_history_entry(("user", "hello")) == ("user", "hello", "")
    assert module._parse_history_entry(("assistant", "hi", "think")) == (
        "assistant",
        "hi",
        "think",
    )


def test_save_reasoning_effort_updates_user_preferences_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module, _, user_paths = _load_agent_panel_module(monkeypatch, tmp_path)
    shared_config_path = tmp_path / "data" / "config.json"
    shared_config_path.parent.mkdir(parents=True, exist_ok=True)
    shared_config_path.write_text(
        json.dumps(
            {
                "llm": {
                    "api_key": "secret",
                    "reasoning": {"effort": "medium", "summary": "auto"},
                }
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    user_paths.preferences.parent.mkdir(parents=True, exist_ok=True)
    user_paths.preferences.write_text(
        json.dumps(
            {"llm": {"reasoning": {"effort": "medium", "summary": "auto"}}},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    assert module._save_reasoning_effort("high") is None

    prefs = json.loads(user_paths.preferences.read_text(encoding="utf-8"))
    assert prefs["llm"]["reasoning"]["effort"] == "high"
    shared = json.loads(shared_config_path.read_text(encoding="utf-8"))
    assert shared["llm"]["reasoning"]["effort"] == "medium"


def test_merged_reasoning_text_joins_rounds(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module, _, _ = _load_agent_panel_module(monkeypatch, tmp_path)
    segments = ["round one"]
    parts = ["round two"]
    merged = module._merged_reasoning_text(segments, parts)
    assert "round one" in merged
    assert "round two" in merged
    assert module.REASONING_ROUND_SEPARATOR in merged


def test_append_assistant_message(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module, fake_streamlit, _ = _load_agent_panel_module(monkeypatch, tmp_path)
    fake_streamlit.session_state = {}
    module.append_assistant_message("Hello from forge")
    history = fake_streamlit.session_state["studio_chat_history"]
    assert history == [("assistant", "Hello from forge", "")]
