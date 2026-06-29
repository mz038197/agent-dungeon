from __future__ import annotations

import os
from pathlib import Path


LOCAL_ENV_DIR = Path.home() / ".agent_dungeon"
LOCAL_ENV_PATH = LOCAL_ENV_DIR / "local.env"

# Always prefer ~/.agent_dungeon/local.env over pre-existing shell env for these keys.
LOCAL_ENV_OVERRIDE_KEYS = frozenset(
    {
        "PUBLIC_URL",
        "PEAS_AGENT_HOME",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "GOOGLE_OAUTH_REDIRECT_URI",
        "SESSION_SECRET",
        "PEAS_LLM_API_KEY",
        "PEAS_LLM_MODEL",
        "PEAS_LLM_BASE_URL",
        "PEAS_TTS_API_KEY",
        "PEAS_TTS_BASE_URL",
    }
)


def load_local_env() -> None:
    """Load KEY=value lines from ~/.agent_dungeon/local.env into os.environ."""
    if not LOCAL_ENV_PATH.is_file():
        return
    text = LOCAL_ENV_PATH.read_text(encoding="utf-8-sig")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        if not key:
            continue
        if key not in os.environ or key in LOCAL_ENV_OVERRIDE_KEYS:
            os.environ[key] = value.strip()


def ensure_cloud_defaults() -> None:
    os.environ.setdefault("STUDIO_CLOUD_MODE", "1")
    if not os.environ.get("PEAS_AGENT_HOME"):
        os.environ["PEAS_AGENT_HOME"] = str(LOCAL_ENV_DIR / "data")
    os.environ.setdefault("PUBLIC_URL", "http://127.0.0.1:8501")


def bootstrap_environment() -> None:
    load_local_env()
    ensure_cloud_defaults()
