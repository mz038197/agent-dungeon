from __future__ import annotations

import streamlit as st

from auth.gate import render_login_gate
from auth.session import get_auth_user
from bootstrap_config import apply_config_override, bootstrap_shared_config
from cloud_paths import ensure_user_dirs, paths_for_user
from env_loader import bootstrap_environment


def init_dungeon_environment() -> None:
    """Load local.env and shared config. Safe before st.set_page_config."""
    bootstrap_environment()
    bootstrap_shared_config()
    apply_config_override()


def require_dungeon_login() -> None:
    """Stop the page if the user is not authenticated. Call after st.set_page_config."""
    if not render_login_gate():
        st.stop()
    user = get_auth_user(st.session_state)
    if user is not None:
        ensure_user_dirs(paths_for_user(user.google_sub))
