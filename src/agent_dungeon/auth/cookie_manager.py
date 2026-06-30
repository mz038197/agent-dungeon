from __future__ import annotations

import streamlit as st
import extra_streamlit_components as stx

from agent_dungeon.auth.cookie_session import (
    AUTH_COOKIE_NAME,
    cookie_browser_options,
    issue_auth_cookie_value,
    parse_auth_cookie_value,
)
from agent_dungeon.auth.session import AuthUser, local_dev_auth_bypass


_COOKIE_MANAGER_STATE_KEY = "dungeon_auth_cookie_manager"


def _cookie_manager() -> stx.CookieManager:
    """Per-session CookieManager singleton (widgets must not live in @st.cache_*)."""
    if _COOKIE_MANAGER_STATE_KEY not in st.session_state:
        st.session_state[_COOKIE_MANAGER_STATE_KEY] = stx.CookieManager(
            key="dungeon_auth_cookie_manager"
        )
    return st.session_state[_COOKIE_MANAGER_STATE_KEY]


def auth_cookie_enabled() -> bool:
    return not local_dev_auth_bypass()


def read_auth_cookie() -> tuple[str | None, bool]:
    """Return (cookie value, manager_ready). manager_ready=False → caller should rerun once."""
    if not auth_cookie_enabled():
        return None, True
    cookies = _cookie_manager().get_all()
    if cookies is None:
        return None, False
    raw = cookies.get(AUTH_COOKIE_NAME)
    if raw is None:
        return None, True
    return str(raw), True


def persist_auth_cookie(user: AuthUser) -> None:
    if not auth_cookie_enabled():
        return
    value = issue_auth_cookie_value(user)
    if value is None:
        return
    options = cookie_browser_options()
    _cookie_manager().set(
        AUTH_COOKIE_NAME,
        value,
        max_age=int(options["max_age"]),
        path=str(options["path"]),
        secure=bool(options["secure"]),
        same_site=str(options["same_site"]),
    )


def delete_auth_cookie() -> None:
    if not auth_cookie_enabled():
        return
    _cookie_manager().delete(AUTH_COOKIE_NAME)


def restore_auth_user_from_cookie() -> tuple[AuthUser | None, bool]:
    raw, ready = read_auth_cookie()
    if not ready:
        return None, False
    if not raw:
        return None, True
    user = parse_auth_cookie_value(raw)
    if user is None:
        delete_auth_cookie()
        return None, True
    return user, True
