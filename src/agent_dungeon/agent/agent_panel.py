from __future__ import annotations

import base64
import contextlib
import io
import json
import uuid
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st
from openai_tts import Settings, stream_tts_play
from openai_tts.settings import MAX_TTS_SPEED, MIN_TTS_SPEED
from st_multimodal_chatinput import multimodal_chatinput

from agent_dungeon.auth.session import get_auth_user
from agent_dungeon.core.bootstrap_config import (
    DEFAULT_TTS_BASE_URL,
    DEFAULT_TTS_MODEL,
    default_tts_config,
    ensure_tts_config_file,
    normalize_tts_config,
    read_tts_config,
    save_tts_config,
    write_effective_config,
)
from agent_dungeon.core.cloud_paths import APP_ROOT, UserPaths, LEVEL_PAGES_DIR, paths_for_user
from agent_dungeon.ui.shell_ui import inject_multimodal_chatinput_theme_fix

REASONING_EFFORT_OPTIONS = ("none", "low", "medium", "high")
REASONING_EFFORT_LABELS = {
    "none": "關閉 (none)",
    "low": "快速 (low)",
    "medium": "平衡 (medium)",
    "high": "深度 (high)",
}
MAX_CHAT_IMAGE_BYTES = 5 * 1024 * 1024
CHAT_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp"})
MIME_TO_CHAT_IMAGE_SUFFIX = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
}
TTS_VOICE_OPTIONS = [
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
]
TTS_VOICE_LABELS: dict[str, str] = {
    "alloy": "中性 · 音色均衡",
    "ash": "男聲 · 偏低沉、語速平穩",
    "ballad": "男聲 · 柔和、節奏偏慢",
    "coral": "女聲 · 溫暖、親切",
    "echo": "男聲 · 清晰、標準",
    "fable": "男聲 · 英式口音、適合旁白",
    "nova": "女聲 · 明亮、有活力",
    "onyx": "男聲 · 低沉、穩重",
    "sage": "女聲 · 沉穩、較內斂",
    "shimmer": "女聲 · 輕快、偏年輕",
}
REASONING_ROUND_SEPARATOR = "\n\n---\n\n"
TOOL_RUN_PLACEHOLDER = "（執行工具中…）"
PANEL_CTX_KEY = "agent_panel_ctx"


@dataclass(frozen=True)
class _PanelCtx:
    user_paths: UserPaths
    sessions_dir: Path
    chat_images_dir: Path
    preferences_path: Path
    effective_config_path: Path
    tts_config_path: Path
    activation_marker: Path


def _user_paths() -> UserPaths | None:
    user = get_auth_user(st.session_state)
    if user is None:
        return None
    return paths_for_user(user.google_sub)


def _init_panel_ctx(paths: UserPaths) -> _PanelCtx:
    ctx = _PanelCtx(
        user_paths=paths,
        sessions_dir=paths.sessions,
        chat_images_dir=paths.chat_images,
        preferences_path=paths.preferences,
        effective_config_path=paths.effective_config,
        tts_config_path=paths.tts,
        activation_marker=paths.root / ".agent_core_activated",
    )
    st.session_state[PANEL_CTX_KEY] = ctx
    return ctx


def _require_ctx() -> _PanelCtx:
    user = get_auth_user(st.session_state)
    if user is None:
        raise RuntimeError("Agent panel context 尚未初始化")
    paths = paths_for_user(user.google_sub)
    ctx = st.session_state.get(PANEL_CTX_KEY)
    if not isinstance(ctx, _PanelCtx) or ctx.user_paths.google_sub != user.google_sub:
        ctx = _init_panel_ctx(paths)
    return ctx


def _display_path(path: Path) -> str:
    return path.resolve().as_posix()


def _studio_context() -> str:
    pages_dir = _display_path(LEVEL_PAGES_DIR)
    data_dir = _display_path(APP_ROOT / "data")
    return "\n".join(
        [
            "【Agent Dungeon 雲端版】左欄為 Streamlit 關卡頁面；右欄為 peas-agent-core Agent。",
            f"【路徑】專案根：{_display_path(APP_ROOT)}；左欄頁面：{pages_dir}；"
            f"共享模板 JSON：{data_dir}/{{slug}}.json。",
            "【左欄↔Agent】render_main → format_extra_context，每則訊息附【目前頁面狀態】。",
            "使用者 workspace 在個人目錄；新增頁面請用 pages/N_Name.py 格式。",
        ]
    )


def _tts_voice_label(voice_id: str) -> str:
    label = TTS_VOICE_LABELS.get(voice_id)
    if label:
        return f"{label}（{voice_id}）"
    return voice_id


def _ensure_user_dirs() -> None:
    ctx = _require_ctx()
    ctx.sessions_dir.mkdir(parents=True, exist_ok=True)
    ctx.chat_images_dir.mkdir(parents=True, exist_ok=True)


def _default_tts_config() -> dict[str, object]:
    return default_tts_config()


def _read_tts_config() -> tuple[dict[str, object], bool]:
    return read_tts_config(_require_ctx().tts_config_path)


def _load_tts_config() -> dict[str, object]:
    prefs, _needs_repair = _read_tts_config()
    return prefs


def _save_tts_config(settings: dict[str, object]) -> str | None:
    return save_tts_config(_require_ctx().tts_config_path, settings)


def _ensure_tts_config_file() -> str | None:
    return ensure_tts_config_file(_require_ctx().tts_config_path)


def _tts_widgets_from_config(config: dict[str, object]) -> dict[str, object]:
    return {
        "studio_tts_enabled": config["enabled"],
        "studio_tts_voice": config["voice"],
        "studio_tts_instructions": config["instructions"],
        "studio_tts_speed": config["speed"],
    }


def _config_from_tts_widgets() -> dict[str, object]:
    current = _load_tts_config()
    return {
        "api_key": current.get("api_key", ""),
        "base_url": current.get("base_url", DEFAULT_TTS_BASE_URL),
        "model": current.get("model", DEFAULT_TTS_MODEL),
        "enabled": bool(st.session_state.get("studio_tts_enabled", False)),
        "voice": str(st.session_state.get("studio_tts_voice", "")),
        "instructions": str(st.session_state.get("studio_tts_instructions", "")),
        "speed": float(st.session_state.get("studio_tts_speed", 1.0)),
    }


def _sync_tts_preferences_for_page(page_name: str) -> str | None:
    settings_error = _ensure_tts_config_file()
    if settings_error is not None:
        return settings_error

    persist_error = _persist_tts_preferences_if_changed()
    if persist_error is not None:
        return persist_error

    _reload_tts_preferences_from_file()
    st.session_state["_studio_tts_page_name"] = page_name
    return None


def _reload_tts_preferences_from_file() -> None:
    prefs = _load_tts_config()
    widgets = _tts_widgets_from_config(prefs)
    for key, value in widgets.items():
        st.session_state[key] = value
    st.session_state["_studio_tts_snapshot"] = dict(prefs)


def _persist_tts_preferences_if_changed() -> str | None:
    required_keys = {
        "studio_tts_enabled",
        "studio_tts_voice",
        "studio_tts_instructions",
        "studio_tts_speed",
    }
    if not required_keys.issubset(st.session_state):
        return None

    normalized = normalize_tts_config(_config_from_tts_widgets())
    previous = st.session_state.get("_studio_tts_snapshot")
    if previous is None or previous == normalized:
        return None

    error = _save_tts_config(normalized)
    if error is not None:
        return error
    st.session_state["_studio_tts_snapshot"] = dict(normalized)
    return None


def _prepare_tts_preferences(page_name: str) -> str | None:
    return _sync_tts_preferences_for_page(page_name)


def _build_tts_settings_for_playback() -> Settings | None:
    if not st.session_state.get("studio_tts_enabled", False):
        return None
    cfg = _load_tts_config()
    api_key = str(cfg.get("api_key", "")).strip()
    if not api_key:
        return None
    model = str(cfg.get("model", "")).strip()
    if not model or "@" not in model:
        return None
    base_url = str(cfg.get("base_url", "")).strip()
    return replace(
        Settings(),
        api_key=api_key,
        base_url=base_url,
        model=model,
        voice=str(st.session_state["studio_tts_voice"]),
        instructions=str(st.session_state["studio_tts_instructions"]).strip()
        or Settings().instructions,
        speed=float(st.session_state["studio_tts_speed"]),
    )


def _render_tts_settings_ui(*, settings_error: str | None = None) -> None:
    ctx = _require_ctx()
    if settings_error:
        st.warning(settings_error)

    voice_options = list(TTS_VOICE_OPTIONS)
    current_voice = str(st.session_state.get("studio_tts_voice", Settings().voice))
    if current_voice not in voice_options:
        voice_options.insert(0, current_voice)

    with st.expander("語音播放", expanded=False):
        st.checkbox(
            "語音播放",
            key="studio_tts_enabled",
            help="開啟後，Agent 文字回答完成後會播放語音。",
        )
        st.selectbox(
            "聲音",
            voice_options,
            format_func=_tts_voice_label,
            key="studio_tts_voice",
            disabled=not st.session_state.get("studio_tts_enabled", False),
        )
        st.text_area(
            "語氣指示",
            key="studio_tts_instructions",
            height=100,
            disabled=not st.session_state.get("studio_tts_enabled", False),
        )
        st.number_input(
            "語速",
            min_value=MIN_TTS_SPEED,
            max_value=MAX_TTS_SPEED,
            step=0.05,
            format="%.2f",
            key="studio_tts_speed",
            disabled=not st.session_state.get("studio_tts_enabled", False),
        )
        st.caption(
            f"TTS 設定檔：`{ctx.tts_config_path}`（含 api_key）。"
            "文字回答完成後才開始 TTS；語音錯誤不會影響文字顯示。"
        )
        persist_error = _persist_tts_preferences_if_changed()
        if persist_error:
            st.warning(persist_error)


def _default_reasoning_config() -> dict[str, str]:
    return {"effort": "medium", "summary": "auto"}


def _read_preferences() -> dict[str, object]:
    path = _require_ctx().preferences_path
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _read_effective_config() -> dict[str, object]:
    path = _require_ctx().effective_config_path
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _normalize_reasoning_effort(value: object) -> str:
    effort = str(value or "").strip().lower()
    if effort in REASONING_EFFORT_OPTIONS:
        return effort
    return _default_reasoning_config()["effort"]


def _load_reasoning_effort() -> str:
    cfg = _read_preferences()
    llm = cfg.get("llm")
    if not isinstance(llm, dict):
        return _default_reasoning_config()["effort"]
    reasoning = llm.get("reasoning")
    if not isinstance(reasoning, dict):
        return _default_reasoning_config()["effort"]
    return _normalize_reasoning_effort(reasoning.get("effort"))


def _load_use_responses_api() -> bool:
    cfg = _read_effective_config()
    llm = cfg.get("llm")
    if not isinstance(llm, dict):
        return True
    return llm.get("use_responses_api") is not False


def _save_reasoning_effort(effort: str) -> str | None:
    ctx = _require_ctx()
    normalized = _normalize_reasoning_effort(effort)
    cfg = _read_preferences()
    llm = cfg.get("llm")
    if not isinstance(llm, dict):
        llm = {}
        cfg["llm"] = llm
    reasoning = llm.get("reasoning")
    if not isinstance(reasoning, dict):
        reasoning = dict(_default_reasoning_config())
        llm["reasoning"] = reasoning
    reasoning["effort"] = normalized
    try:
        ctx.preferences_path.parent.mkdir(parents=True, exist_ok=True)
        ctx.preferences_path.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        return f"無法寫入 LLM 設定檔：{exc}"
    return None


def _reload_reasoning_llm_config(agent: Any) -> str | None:
    reload = getattr(agent, "reload_llm_config", None)
    if reload is None:
        return "請先升級 peas-agent-core（需支援 Agent.reload_llm_config）。"
    try:
        reload()
    except Exception as exc:
        return f"套用推理深度失敗：`{exc}`"
    return None


def _apply_reasoning_effort_change(new_effort: str) -> str | None:
    error = _save_reasoning_effort(new_effort)
    if error:
        return error
    user = get_auth_user(st.session_state)
    if user is not None:
        write_effective_config(user.google_sub)
    agent = st.session_state.get("studio_agent")
    if agent is not None:
        return _reload_reasoning_llm_config(agent)
    return None


def _reload_reasoning_preferences_from_file() -> None:
    effort = _load_reasoning_effort()
    st.session_state["studio_reasoning_effort"] = effort
    st.session_state["_studio_reasoning_snapshot"] = effort


def _persist_reasoning_effort_if_changed() -> str | None:
    if "studio_reasoning_effort" not in st.session_state:
        return None
    previous = st.session_state.get("_studio_reasoning_snapshot")
    if previous is None:
        return None
    current = _normalize_reasoning_effort(st.session_state.get("studio_reasoning_effort"))
    if previous == current:
        return None
    reload_error = _apply_reasoning_effort_change(current)
    if reload_error:
        return reload_error
    st.session_state["_studio_reasoning_snapshot"] = current
    return None


def _sync_reasoning_preferences_for_page(page_name: str) -> str | None:
    persist_error = _persist_reasoning_effort_if_changed()
    if persist_error is not None:
        return persist_error
    _reload_reasoning_preferences_from_file()
    st.session_state["_studio_reasoning_page_name"] = page_name
    return None


def _prepare_reasoning_preferences(page_name: str) -> str | None:
    return _sync_reasoning_preferences_for_page(page_name)


def _render_reasoning_settings_ui(*, settings_error: str | None = None) -> None:
    ctx = _require_ctx()
    if settings_error:
        st.warning(settings_error)

    responses_enabled = _load_use_responses_api()
    with st.expander("推理深度", expanded=False):
        st.selectbox(
            "推理深度",
            REASONING_EFFORT_OPTIONS,
            format_func=lambda value: REASONING_EFFORT_LABELS.get(value, value),
            key="studio_reasoning_effort",
            disabled=not responses_enabled,
            help="控制 Responses API 的 reasoning.effort；切換後立即套用。",
        )
        if not responses_enabled:
            st.caption("需於 config.json 啟用 use_responses_api 才有效。")
        else:
            st.caption(
                "關閉 (none) 可加速回覆；若 API 回 400 請改回 low 或確認模型是否支援 none。"
            )
        st.caption(f"你的偏好設定：`{ctx.preferences_path}`")
        persist_error = _persist_reasoning_effort_if_changed()
        if persist_error:
            st.warning(persist_error)


def _clear_agent_cache() -> None:
    st.session_state.pop("studio_agent", None)
    st.session_state.pop("studio_agent_session_name", None)
    st.session_state["studio_agent_core_connected"] = False


def _write_activation_marker() -> None:
    ctx = _require_ctx()
    ctx.activation_marker.parent.mkdir(parents=True, exist_ok=True)
    ctx.activation_marker.write_text(
        datetime.now().isoformat(timespec="seconds"),
        encoding="utf-8",
    )


def _remove_activation_marker() -> None:
    ctx = _require_ctx()
    if ctx.activation_marker.exists():
        ctx.activation_marker.unlink()


def _suffix_from_mime(mime: str) -> str | None:
    normalized = mime.lower().split(";", 1)[0].strip()
    return MIME_TO_CHAT_IMAGE_SUFFIX.get(normalized)


def _suffix_from_filename(name: str) -> str | None:
    suffix = Path(name).suffix.lower()
    if suffix in CHAT_IMAGE_SUFFIXES:
        return suffix
    return None


def _validate_chat_image(data: bytes, suffix: str) -> str | None:
    if len(data) > MAX_CHAT_IMAGE_BYTES:
        return "圖片超過 5 MB，請先壓縮後再上傳。"
    if suffix not in CHAT_IMAGE_SUFFIXES:
        return "只支援 PNG、JPG、JPEG、WEBP 圖片。"
    return None


def _save_chat_image_bytes(data: bytes, *, suffix: str) -> tuple[str | None, str | None]:
    error = _validate_chat_image(data, suffix)
    if error:
        return None, error

    ctx = _require_ctx()
    _ensure_user_dirs()
    filename = f"chat_image_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}{suffix}"
    target = ctx.chat_images_dir / filename
    target.write_bytes(data)
    return str(target.resolve()), None


def _pending_image_from_bytes(
    *, data: bytes, suffix: str, name: str, mime: str
) -> tuple[dict[str, Any] | None, str | None]:
    error = _validate_chat_image(data, suffix)
    if error:
        return None, error
    return {"bytes": data, "suffix": suffix, "name": name, "mime": mime}, None


def _pending_image_from_multimodal_file(
    file_info: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    mime = str(file_info.get("type", "") or "")
    if not mime.startswith("image/"):
        return None, "只支援 PNG、JPG、JPEG、WEBP 圖片。"

    suffix = _suffix_from_mime(mime) or _suffix_from_filename(str(file_info.get("name", "") or ""))
    if suffix is None:
        return None, "只支援 PNG、JPG、JPEG、WEBP 圖片。"

    raw_content = file_info.get("content", "")
    if not raw_content:
        return None, "無法讀取貼上的圖片內容。"

    try:
        data = base64.b64decode(raw_content)
    except (ValueError, TypeError):
        return None, "無法讀取貼上的圖片內容。"

    name = str(file_info.get("name", "") or f"pasted{suffix}")
    return _pending_image_from_bytes(data=data, suffix=suffix, name=name, mime=mime)


def _multimodal_user_text(chatinput: dict[str, Any]) -> str:
    return str(chatinput.get("textInput") or chatinput.get("text") or "").strip()


def _pending_image_from_data_url(
    data_url: str,
    *,
    index: int = 0,
) -> tuple[dict[str, Any] | None, str | None]:
    if not data_url.startswith("data:") or "," not in data_url:
        return None, "無法讀取貼上的圖片內容。"

    header, encoded = data_url.split(",", 1)
    mime = header.split(":", 1)[1].split(";", 1)[0].strip().lower()
    suffix = _suffix_from_mime(mime)
    if suffix is None:
        return None, "只支援 PNG、JPG、JPEG、WEBP 圖片。"

    try:
        data = base64.b64decode(encoded)
    except (ValueError, TypeError):
        return None, "無法讀取貼上的圖片內容。"

    name = f"pasted_{index + 1}{suffix}"
    return _pending_image_from_bytes(data=data, suffix=suffix, name=name, mime=mime)


def _resolve_submission_image(
    chatinput: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    multimodal_files = chatinput.get("uploadedFiles") or []
    image_files = [
        file_info
        for file_info in multimodal_files
        if str(file_info.get("type", "") or "").startswith("image/")
    ]
    if image_files:
        return _pending_image_from_multimodal_file(image_files[-1])

    data_urls = chatinput.get("images") or []
    if data_urls:
        return _pending_image_from_data_url(str(data_urls[-1]), index=len(data_urls) - 1)

    return None, None


def _chat_submission_token(chatinput: dict[str, Any]) -> str:
    text = _multimodal_user_text(chatinput)
    files = chatinput.get("uploadedFiles") or []
    image_names = sorted(
        str(file_info.get("name", "") or "")
        for file_info in files
        if str(file_info.get("type", "") or "").startswith("image/")
    )
    if not image_names:
        image_names = [f"data-url:{idx}" for idx, _ in enumerate(chatinput.get("images") or [])]
    return f"{text}\0{','.join(image_names)}"


def _new_session_path() -> Path:
    ctx = _require_ctx()
    _ensure_user_dirs()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shortid = uuid.uuid4().hex[:6]
    path = ctx.sessions_dir / f"session_{stamp}_{shortid}.jsonl"
    path.touch(exist_ok=False)
    return path


def _session_sort_time(path: Path) -> datetime:
    created_at: str | None = None
    try:
        with path.open(encoding="utf-8") as f:
            first = f.readline().strip()
        if first:
            obj = json.loads(first)
            if isinstance(obj, dict):
                created_at = obj.get("created_at")
    except (OSError, json.JSONDecodeError):
        created_at = None

    if created_at:
        try:
            return datetime.fromisoformat(created_at)
        except ValueError:
            pass
    return datetime.fromtimestamp(path.stat().st_mtime)


def _session_label(path: Path) -> str:
    ts = _session_sort_time(path)
    shortid = path.stem.split("_")[-1]
    return f"{ts:%H:%M:%S} · 雲端 · {shortid}"


def _session_name(path: Path) -> str:
    return path.name


def _is_valid_session_name(value: str) -> bool:
    ctx = _require_ctx()
    if not value or not value.endswith(".jsonl"):
        return False
    if value != Path(value).name or ".." in value:
        return False
    return (ctx.sessions_dir / value).is_file()


def _coerce_session_name(value: str) -> str | None:
    if _is_valid_session_name(value):
        return value
    candidate = Path(value).name
    if _is_valid_session_name(candidate):
        return candidate
    return None


def _resolve_session_picker_value(value: str, labels: dict[str, str]) -> str | None:
    coerced = _coerce_session_name(value)
    if coerced:
        return coerced
    for session_name, label in labels.items():
        if value == label:
            return session_name
    return None


def _build_session_picker_options(
    sessions: list[Path],
) -> tuple[list[str], dict[str, str]]:
    labels = {_session_name(path): _session_label(path) for path in sessions}
    return list(labels), labels


def _list_sessions() -> list[Path]:
    ctx = _require_ctx()
    _ensure_user_dirs()
    return sorted(
        ctx.sessions_dir.glob("session_*.jsonl"),
        key=_session_sort_time,
        reverse=True,
    )


def _extract_display_user_text(text: str) -> str:
    marker = "\n\n使用者問題："
    if marker in text:
        return text.rsplit(marker, 1)[-1].strip()
    return text


def _load_session_history(path: Path) -> list[tuple[str, str, str]]:
    history: list[tuple[str, str, str]] = []
    if not path.exists():
        return history

    try:
        with path.open(encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(obj, dict) or obj.get("_type") == "metadata":
                    continue

                role = obj.get("role")
                content = str(obj.get("content", "") or "").strip()
                if role == "user" and content:
                    history.append(("user", _extract_display_user_text(content), ""))
                elif role == "assistant" and content:
                    history.append(("assistant", content, ""))
    except OSError:
        return history
    return history


def _commit_reasoning_round(segments: list[str], current_parts: list[str]) -> None:
    text = "".join(current_parts).strip()
    if text:
        segments.append(text)
    current_parts.clear()


def _merged_reasoning_text(segments: list[str], current_parts: list[str]) -> str:
    parts = [segment for segment in segments if segment.strip()]
    current = "".join(current_parts).strip()
    if current:
        parts.append(current)
    return REASONING_ROUND_SEPARATOR.join(parts)


def _render_reasoning_expander(
    reasoning_slot: Any,
    text: str,
    *,
    expanded: bool,
    stream_ui: dict[str, Any],
) -> None:
    if not text.strip():
        return
    stream_ui["visible"] = True
    stream_ui["expanded"] = expanded
    with reasoning_slot.container():
        with st.expander("思考過程", expanded=expanded):
            if expanded:
                stream_ui["reasoning_ph"] = st.empty()
                stream_ui["reasoning_ph"].markdown(text)
            else:
                stream_ui["reasoning_ph"] = None
                st.markdown(text)


def _parse_history_entry(entry: tuple[str, ...]) -> tuple[str, str, str]:
    role = entry[0]
    text = entry[1] if len(entry) > 1 else ""
    reasoning = entry[2] if len(entry) > 2 else ""
    return role, text, reasoning


def _render_history_message(role: str, text: str, *, reasoning: str = "") -> None:
    with st.chat_message(role):
        if role == "assistant" and reasoning.strip():
            with st.expander("思考過程", expanded=False):
                st.markdown(reasoning)
        st.markdown(text)


def _set_current_session(path: Path) -> None:
    session_name = _session_name(path)
    st.session_state["session_name"] = session_name
    st.session_state.pop("session_path", None)
    st.session_state["studio_chat_history"] = _load_session_history(path)
    st.session_state.pop("studio_agent", None)
    st.session_state.pop("studio_agent_session_name", None)


def _ensure_valid_current_session(sessions: list[Path]) -> str | None:
    current = st.session_state.get("session_name")
    if not current:
        legacy = st.session_state.get("session_path")
        if legacy:
            current = _coerce_session_name(str(legacy))
            if current:
                st.session_state["session_name"] = current
                st.session_state.pop("session_path", None)

    if current and _is_valid_session_name(current):
        return current

    st.session_state.pop("session_name", None)
    st.session_state.pop("session_path", None)
    st.session_state.pop("studio_agent", None)
    st.session_state.pop("studio_agent_session_name", None)
    if sessions:
        _set_current_session(sessions[0])
        return st.session_state["session_name"]
    return None


def _reset_session_picker_widget() -> None:
    st.session_state["session_picker_version"] = (
        st.session_state.get("session_picker_version", 0) + 1
    )


def _create_agent_for_session(session_name: str) -> Any:
    ctx = _require_ctx()
    if not _is_valid_session_name(session_name):
        raise RuntimeError(f"對話紀錄無效：{session_name!r}")
    user = get_auth_user(st.session_state)
    if user is None:
        raise RuntimeError("未登入")
    write_effective_config(user.google_sub)
    try:
        from peas_agent import Agent
    except ImportError as exc:
        raise RuntimeError(
            "找不到 peas-agent-core。請確認已安裝 peas-agent-core 依賴。"
        ) from exc
    return Agent.create(
        workspace=ctx.user_paths.workspace,
        session_name=session_name,
        project_root=APP_ROOT,
        host_context=_studio_context(),
        config_path=ctx.effective_config_path,
    )


def _get_agent_for_session(session_name: str) -> Any:
    if (
        "studio_agent" not in st.session_state
        or st.session_state.get("studio_agent_session_name") != session_name
    ):
        st.session_state["studio_agent"] = _create_agent_for_session(session_name)
        st.session_state["studio_agent_session_name"] = session_name
        st.session_state["studio_agent_core_connected"] = True
    return st.session_state["studio_agent"]


def _activate_agent_core(session_name: str) -> tuple[bool, str]:
    _clear_agent_cache()
    try:
        agent = _create_agent_for_session(session_name)
    except RuntimeError as exc:
        _remove_activation_marker()
        return False, str(exc)
    except Exception as exc:
        _remove_activation_marker()
        return False, f"Agent Core 啟用失敗：{exc}"

    st.session_state["studio_agent"] = agent
    st.session_state["studio_agent_session_name"] = session_name
    st.session_state["studio_agent_core_connected"] = True
    _write_activation_marker()
    return True, "Agent Core 已連接。"


def _restore_agent_core_if_possible(session_name: str) -> tuple[bool, str | None]:
    if st.session_state.get("studio_agent_core_connected"):
        return True, None
    ctx = _require_ctx()
    if not ctx.activation_marker.exists():
        return False, None
    ok, message = _activate_agent_core(session_name)
    if ok:
        return True, None
    return False, message


def append_assistant_message(text: str) -> None:
    """Append a non-LLM assistant line (e.g. Forge Lab stdout) to chat history."""
    message = text.strip()
    if not message:
        return
    history = st.session_state.get("studio_chat_history")
    if not isinstance(history, list):
        history = []
    history.append(("assistant", message, ""))
    st.session_state["studio_chat_history"] = history


def render_chat_panel(*, extra_context: str = "", page_name: str = "") -> None:
    paths = _user_paths()
    if paths is None:
        st.warning("請先登入。")
        return

    _init_panel_ctx(paths)
    _ensure_user_dirs()

    st.markdown('<div class="studio-agent-title-spacer"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="studio-agent-title-text">我的 Agent</div>',
        unsafe_allow_html=True,
    )

    sessions = _list_sessions()
    if not sessions:
        _set_current_session(_new_session_path())
        sessions = _list_sessions()
    if "session_name" not in st.session_state and "session_path" not in st.session_state and sessions:
        _set_current_session(sessions[0])
    current_session = _ensure_valid_current_session(sessions)

    if "studio_chat_history" not in st.session_state:
        st.session_state["studio_chat_history"] = [
            (
                "assistant",
                "請先按「啟用 Agent」。啟用後，我會讀取左欄傳來的頁面狀態，再回答你的問題。",
                "",
            )
        ]

    ids, labels = _build_session_picker_options(sessions)
    if current_session and current_session not in labels and _is_valid_session_name(current_session):
        ids.insert(0, current_session)
        labels[current_session] = "剛剛 · 目前對話"

    pick_col, new_col, del_col = st.columns([6, 1, 1])
    if ids:
        picker_key = f"session_picker_{st.session_state.get('session_picker_version', 0)}"
        selected_index = ids.index(current_session) if current_session in ids else 0
        picked_id = pick_col.selectbox(
            "對話紀錄",
            ids,
            index=selected_index,
            format_func=lambda value: labels.get(value, value),
            label_visibility="collapsed",
            key=picker_key,
        )
        resolved_pick = _resolve_session_picker_value(picked_id, labels)
        if resolved_pick and resolved_pick != current_session:
            ctx = _require_ctx()
            _set_current_session(ctx.sessions_dir / resolved_pick)
            st.rerun()
    else:
        pick_col.caption("尚無對話紀錄")
    if new_col.button("", icon=":material/add:", help="新增對話", use_container_width=True):
        _set_current_session(_new_session_path())
        _reset_session_picker_widget()
        st.rerun()
    if del_col.button(
        "",
        icon=":material/delete:",
        help="刪除對話",
        use_container_width=True,
        disabled=not current_session,
    ):
        if current_session:
            ctx = _require_ctx()
            target = ctx.sessions_dir / current_session
            if target.exists():
                target.unlink()
            st.session_state.pop("session_name", None)
            st.session_state.pop("session_path", None)
            st.session_state.pop("studio_chat_history", None)
            st.session_state.pop("studio_agent", None)
            st.session_state.pop("studio_agent_session_name", None)
            remaining = _list_sessions()
            if remaining:
                _set_current_session(remaining[0])
            else:
                _clear_agent_cache()
                _remove_activation_marker()
            _reset_session_picker_widget()
            st.rerun()

    settings_error = _prepare_tts_preferences(page_name)
    reasoning_error = _prepare_reasoning_preferences(page_name)

    current_session = st.session_state.get("session_name")
    if not current_session:
        st.caption("尚無對話紀錄，請按 **+** 新增對話。")
        _render_tts_settings_ui(settings_error=settings_error)
        _render_reasoning_settings_ui(settings_error=reasoning_error)
        st.chat_input("詢問...", disabled=True, key="studio_chat_no_session")
        return

    restored, restore_error = _restore_agent_core_if_possible(current_session)
    connected = bool(st.session_state.get("studio_agent_core_connected")) or restored
    status_text = ":green[●] Agent Core：已連接" if connected else ":red[●] Agent Core：未啟用"
    st.markdown(f"**{status_text}**")
    if not connected:
        if restore_error:
            st.warning(restore_error)
        if st.button("啟用 Agent", type="primary", use_container_width=True):
            ok, message = _activate_agent_core(current_session)
            if ok:
                st.success("Agent Core 已連接。你可以開始詢問。")
                st.rerun()
            else:
                st.error(message)
        _render_tts_settings_ui(settings_error=settings_error)
        _render_reasoning_settings_ui(settings_error=reasoning_error)
        st.chat_input("請先啟用 Agent...", disabled=True, key="studio_chat_not_activated")
        return

    ctx = _require_ctx()
    with st.expander("技術資訊", expanded=False):
        st.caption(f"對話紀錄檔：{ctx.sessions_dir / current_session}")
        st.caption(f"語音設定檔：{ctx.tts_config_path}")
        st.caption(f"偏好設定：{ctx.preferences_path}")
        st.caption(f"Agent 執行設定：{ctx.effective_config_path}")
        if page_name:
            st.caption(f"目前頁面：{page_name}")

    _render_tts_settings_ui(settings_error=settings_error)
    _render_reasoning_settings_ui(settings_error=reasoning_error)

    try:
        agent = _get_agent_for_session(current_session)
    except RuntimeError as exc:
        st.error(str(exc))
        _clear_agent_cache()
        _remove_activation_marker()
        st.chat_input("詢問 Agent...", disabled=True, key="studio_chat_no_key")
        return
    except Exception as exc:
        st.error(f"Agent Core 連線失敗：`{exc}`")
        _clear_agent_cache()
        _remove_activation_marker()
        st.chat_input("詢問 Agent...", disabled=True, key="studio_chat_connect_failed")
        return

    chat = st.container(height=460, border=True)
    with chat:
        for entry in st.session_state["studio_chat_history"]:
            role, text, reasoning = _parse_history_entry(entry)
            _render_history_message(role, text, reasoning=reasoning)

    st.caption("輸入文字後 Enter 送出；可 Ctrl+V 貼圖，或點輸入框內圖片按鈕選檔（PNG/JPG/WEBP，上限 5 MB）。")
    inject_multimodal_chatinput_theme_fix()
    chatinput = multimodal_chatinput(
        key=f"studio_multimodal_{current_session}",
    )

    should_process_submission = False
    submission_token = ""
    user_text = ""
    pending_image: dict[str, Any] | None = None
    image_path: str | None = None

    if chatinput is not None:
        submission_token = _chat_submission_token(chatinput)
        if submission_token != st.session_state.get("studio_last_chat_submission_token"):
            user_text = _multimodal_user_text(chatinput)
            pending_image, image_error = _resolve_submission_image(chatinput)
            if image_error:
                st.warning(image_error)
                pending_image = None
            if user_text or pending_image is not None:
                should_process_submission = True

    if should_process_submission:
        if pending_image is not None:
            image_path, save_error = _save_chat_image_bytes(
                pending_image["bytes"],
                suffix=pending_image["suffix"],
            )
            if save_error:
                st.warning(save_error)
                image_path = None
                pending_image = None
            if not user_text and pending_image is None:
                should_process_submission = False

    if should_process_submission:
        st.session_state["studio_last_chat_submission_token"] = submission_token

        display_user_text = user_text
        if image_path:
            attachment_note = user_text or "（已附圖，未輸入文字）"
            display_user_text = f"{attachment_note}\n\n（已附圖：{image_path}）"

        st.session_state["studio_chat_history"].append(("user", display_user_text, ""))

        prompt_user_text = user_text or "（使用者只附上圖片，未輸入文字）"
        if extra_context.strip():
            prompt = f"【目前頁面狀態】\n{extra_context.strip()}\n\n使用者問題：{prompt_user_text}"
        else:
            prompt = f"使用者問題：{prompt_user_text}"

        with chat:
            with st.chat_message("user"):
                if user_text:
                    st.markdown(user_text)
                elif image_path:
                    st.markdown("（已附圖，未輸入文字）")
                if pending_image is not None and image_path:
                    st.image(pending_image["bytes"], caption="已附圖", use_container_width=True)
            with st.chat_message("assistant"):
                reasoning_slot = st.empty()
                placeholder = st.empty()
                answer_parts: list[str] = []
                reasoning_segments: list[str] = []
                reasoning_parts: list[str] = []
                stream_ui: dict[str, Any] = {
                    "reasoning_ph": None,
                    "visible": False,
                    "expanded": False,
                    "answer_started": False,
                }
                tts_settings = _build_tts_settings_for_playback()
                if st.session_state.get("studio_tts_enabled") and tts_settings is None:
                    cfg = _load_tts_config()
                    tts_path = ctx.tts_config_path
                    if not str(cfg.get("api_key", "")).strip():
                        st.warning(f"語音已開啟，但 {tts_path} 尚未設定 api_key。")
                    elif "@" not in str(cfg.get("model", "")).strip():
                        st.warning(
                            "語音已開啟，但 tts.json 的 model 必須使用 router 格式，"
                            f"例如 `{DEFAULT_TTS_MODEL}`。"
                        )

                def _sync_reasoning_ui() -> None:
                    text = _merged_reasoning_text(reasoning_segments, reasoning_parts)
                    if not text:
                        return
                    expanded = not stream_ui["answer_started"]
                    if expanded:
                        if not stream_ui["visible"] or not stream_ui["expanded"]:
                            _render_reasoning_expander(
                                reasoning_slot,
                                text,
                                expanded=True,
                                stream_ui=stream_ui,
                            )
                        elif stream_ui["reasoning_ph"] is not None:
                            stream_ui["reasoning_ph"].markdown(text)
                        else:
                            _render_reasoning_expander(
                                reasoning_slot,
                                text,
                                expanded=True,
                                stream_ui=stream_ui,
                            )
                    else:
                        _render_reasoning_expander(
                            reasoning_slot,
                            text,
                            expanded=False,
                            stream_ui=stream_ui,
                        )

                def on_reasoning(token: str) -> None:
                    reasoning_parts.append(token)
                    _sync_reasoning_ui()

                def on_token(token: str) -> None:
                    if not stream_ui["answer_started"]:
                        stream_ui["answer_started"] = True
                        _sync_reasoning_ui()
                    answer_parts.append(token)
                    placeholder.markdown("".join(answer_parts))

                def on_stream_reset() -> None:
                    _commit_reasoning_round(reasoning_segments, reasoning_parts)
                    answer_parts.clear()
                    stream_ui["answer_started"] = False
                    placeholder.markdown(TOOL_RUN_PLACEHOLDER)
                    merged = _merged_reasoning_text(reasoning_segments, reasoning_parts)
                    if merged:
                        _render_reasoning_expander(
                            reasoning_slot,
                            merged,
                            expanded=True,
                            stream_ui=stream_ui,
                        )

                try:
                    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
                        io.StringIO()
                    ):
                        final_text = agent.chat(
                            prompt,
                            image_path=image_path,
                            on_token=on_token,
                            on_reasoning=on_reasoning,
                            on_stream_reset=on_stream_reset,
                        )
                except Exception as exc:
                    final_text = f"Agent 執行時發生錯誤：`{exc}`"
                    answer = final_text
                    placeholder.error(final_text)
                else:
                    answer = "".join(answer_parts).strip() or final_text.strip()

                _commit_reasoning_round(reasoning_segments, reasoning_parts)
                reasoning_text = _merged_reasoning_text(reasoning_segments, [])
                st.session_state["studio_chat_history"].append(
                    ("assistant", answer, reasoning_text)
                )
                if tts_settings is not None and answer:
                    try:
                        stream_tts_play(answer, tts_settings)
                    except Exception as exc:
                        st.warning(f"語音播放發生錯誤，文字回答已保留：`{exc}`")
                st.rerun()
