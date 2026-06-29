from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent


def is_cloud_mode() -> bool:
    return os.environ.get("STUDIO_CLOUD_MODE", "1") == "1"


def peas_agent_home() -> Path:
    raw = os.environ.get("PEAS_AGENT_HOME", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return Path.home() / ".agent_dungeon" / "data"


def shared_config_path() -> Path:
    return peas_agent_home() / "config.json"


def shared_tts_config_path() -> Path:
    return peas_agent_home() / "tts.json"


def user_root(google_sub: str) -> Path:
    safe = google_sub.strip()
    if not safe:
        raise ValueError("google_sub 不可為空")
    return peas_agent_home() / "users" / safe


@dataclass(frozen=True)
class UserPaths:
    google_sub: str
    root: Path
    profile: Path
    progress: Path
    workspace: Path
    sessions: Path
    page_data: Path
    chat_images: Path


def paths_for_user(google_sub: str) -> UserPaths:
    root = user_root(google_sub)
    workspace = root / "workspace"
    return UserPaths(
        google_sub=google_sub,
        root=root,
        profile=root / "profile.json",
        progress=root / "progress.json",
        workspace=workspace,
        sessions=workspace / "sessions",
        page_data=root / "page_data",
        chat_images=workspace / "uploads" / "chat_images",
    )


def ensure_user_dirs(paths: UserPaths) -> None:
    paths.sessions.mkdir(parents=True, exist_ok=True)
    paths.page_data.mkdir(parents=True, exist_ok=True)
    paths.chat_images.mkdir(parents=True, exist_ok=True)


def write_profile(paths: UserPaths, *, email: str, name: str) -> None:
    payload = {
        "email": email,
        "name": name,
        "google_sub": paths.google_sub,
    }
    paths.profile.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def page_data_path(page_name: str, paths: UserPaths) -> Path:
    slug = page_name.strip().lower().replace(" ", "_")
    return paths.page_data / f"{slug}.json"


def template_page_data_path(page_name: str) -> Path:
    slug = page_name.strip().lower().replace(" ", "_")
    return APP_ROOT / "data" / f"{slug}.json"
