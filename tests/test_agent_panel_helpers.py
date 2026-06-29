from __future__ import annotations

import json
import sys
import types
from importlib import util
from pathlib import Path

import pytest

from cloud_paths import paths_for_user


def _load_agent_panel_module(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    fake_streamlit = types.SimpleNamespace(session_state={})
    fake_openai_tts = types.SimpleNamespace(
        Settings=lambda: types.SimpleNamespace(
            voice="nova",
            instructions="default instructions",
            speed=1.25,
        ),
        stream_tts_play=lambda *_args, **_kwargs: None,
    )
    fake_openai_tts_settings = types.SimpleNamespace(
        MIN_TTS_SPEED=0.25,
        MAX_TTS_SPEED=4.0,
    )

    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    monkeypatch.setitem(sys.modules, "openai_tts", fake_openai_tts)
    monkeypatch.setitem(sys.modules, "openai_tts.settings", fake_openai_tts_settings)
    fake_multimodal = types.ModuleType("st_multimodal_chatinput")
    fake_multimodal.multimodal_chatinput = lambda **_kwargs: None
    monkeypatch.setitem(sys.modules, "st_multimodal_chatinput", fake_multimodal)

    module_path = Path(__file__).parents[1] / "agent_panel.py"
    spec = util.spec_from_file_location("agent_panel_under_test", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = util.module_from_spec(spec)
    sys.modules["agent_panel_under_test"] = module
    spec.loader.exec_module(module)

    home = tmp_path / "data"
    monkeypatch.setenv("PEAS_AGENT_HOME", str(home))
    user_paths = paths_for_user("sub-test")
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


def test_save_reasoning_effort_updates_nested_key_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module, _, user_paths = _load_agent_panel_module(monkeypatch, tmp_path)
    config_path = tmp_path / "data" / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
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
    module._init_panel_ctx(user_paths)

    assert module._save_reasoning_effort("high") is None

    on_disk = json.loads(config_path.read_text(encoding="utf-8"))
    assert on_disk["llm"]["api_key"] == "secret"
    assert on_disk["llm"]["reasoning"]["effort"] == "high"
    assert on_disk["llm"]["reasoning"]["summary"] == "auto"


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
