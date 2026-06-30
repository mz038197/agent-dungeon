from __future__ import annotations

import html
from urllib.parse import unquote

import streamlit as st

from agent_dungeon.auth.google_oauth import GoogleUserClaims
from agent_dungeon.auth.cookie_manager import persist_auth_cookie, restore_auth_user_from_cookie
from agent_dungeon.auth.session import (
    AuthUser,
    OAUTH_STATE_KEY,
    build_oauth_service,
    default_dev_user,
    get_auth_user,
    local_dev_auth_bypass,
    oauth_enabled,
    oauth_redirect_uri,
)
from agent_dungeon.core.bootstrap_config import bootstrap_shared_config, ensure_user_agent_config
from agent_dungeon.core.cloud_paths import ensure_user_dirs, paths_for_user, write_profile
from agent_dungeon.core.env_loader import load_local_env
from agent_dungeon.auth.session import set_auth_user
from agent_dungeon.ui.shell_ui import inject_hide_streamlit_chrome


def _oauth_state(oauth) -> str:
    state = st.session_state.get(OAUTH_STATE_KEY)
    if isinstance(state, str) and oauth.verify_state(state):
        return state
    state = oauth.create_state()
    st.session_state[OAUTH_STATE_KEY] = state
    return state


def _render_oauth_login_link(label: str, url: str) -> None:
    """Same-tab navigation — st.link_button always opens a new tab."""
    safe_label = html.escape(label)
    safe_url = html.escape(url, quote=True)
    st.markdown(
        f'<a class="oauth-login-btn" href="{safe_url}" target="_self" rel="noopener noreferrer">{safe_label}</a>',
        unsafe_allow_html=True,
    )


def _hide_streamlit_chrome() -> None:
    inject_hide_streamlit_chrome(
        hide_sidebar=True,
        extra_css="""
  .block-container { padding-top: 1rem !important; max-width: 520px !important; margin: 0 auto; }
  .login-title { font-size: 2rem; font-weight: 800; text-align: center; margin-bottom: 0.25rem; }
  .login-sub { text-align: center; color: #94a3b8; margin-bottom: 1.5rem; }
  .oauth-login-btn {
    display: block; width: 100%; padding: 0.625rem 1rem; box-sizing: border-box;
    background: #ff4b4b; color: #fff !important; text-align: center;
    text-decoration: none !important; border-radius: 0.5rem; font-weight: 600;
  }
  .oauth-login-btn:hover { background: #ff6b6b; color: #fff !important; }
""",
    )


def _handle_oauth_callback() -> str | None:
    params = st.query_params
    code = params.get("code")
    state = params.get("state")
    error = params.get("error")

    if error:
        st.query_params.clear()
        msg = error[0] if isinstance(error, list) else str(error)
        return f"Google 登入已取消：{msg}"

    if not code and not state:
        return None

    if isinstance(code, list):
        code = code[0] if code else ""
    if isinstance(state, list):
        state = state[0] if state else ""
    code = unquote(str(code).strip())
    state = unquote(str(state).strip())
    if not code or not state:
        st.query_params.clear()
        return "Google 登入參數不完整"

    oauth = build_oauth_service()
    # State is HMAC-signed (see google_oauth.create_state). Do not compare against
    # st.session_state — it is empty after the Google redirect in a new session.
    if not oauth.verify_state(state):
        st.query_params.clear()
        return (
            "Google 登入狀態驗證失敗，請再試一次。"
            "若剛修改過 local.env，請重啟 Streamlit；"
            "並確認瀏覽器網址為 http://127.0.0.1:8501（勿用 localhost）。"
        )

    try:
        claims = oauth.exchange_code(code)
    except ValueError as exc:
        st.query_params.clear()
        return str(exc)
    except Exception:
        st.query_params.clear()
        return "Google 登入失敗，請稍後再試"

    bootstrap_shared_config()
    user = set_auth_user(st.session_state, claims)
    paths = paths_for_user(user.google_sub)
    ensure_user_dirs(paths)
    ensure_user_agent_config(user.google_sub)
    write_profile(paths, email=user.email, name=user.name)
    st.session_state.pop(OAUTH_STATE_KEY, None)
    st.query_params.clear()
    _complete_login(user)
    return None


def _apply_dev_login(claims: GoogleUserClaims) -> None:
    bootstrap_shared_config()
    user = set_auth_user(st.session_state, claims)
    paths = paths_for_user(user.google_sub)
    ensure_user_dirs(paths)
    ensure_user_agent_config(user.google_sub)
    write_profile(paths, email=user.email, name=user.name)


def _apply_authenticated_user(user: AuthUser, *, write_profile_file: bool) -> AuthUser:
    bootstrap_shared_config()
    claims = GoogleUserClaims(
        email=user.email,
        name=user.name,
        google_sub=user.google_sub,
    )
    set_auth_user(st.session_state, claims)
    paths = paths_for_user(user.google_sub)
    ensure_user_dirs(paths)
    if write_profile_file:
        ensure_user_agent_config(user.google_sub)
        write_profile(paths, email=user.email, name=user.name)
    return user


def _complete_login(user: AuthUser) -> None:
    persist_auth_cookie(user)
    st.session_state.pop("_auth_cookie_restore_attempted", None)
    st.rerun()


def _try_restore_auth_from_cookie() -> bool:
    if get_auth_user(st.session_state) is not None:
        return True
    if local_dev_auth_bypass():
        return False

    user, ready = restore_auth_user_from_cookie()
    if not ready:
        if not st.session_state.get("_auth_cookie_restore_attempted"):
            st.session_state["_auth_cookie_restore_attempted"] = True
            st.rerun()
        return False

    st.session_state.pop("_auth_cookie_restore_attempted", None)
    if user is None:
        return False

    _apply_authenticated_user(user, write_profile_file=False)
    return True


def render_login_gate() -> bool:
    load_local_env()

    if get_auth_user(st.session_state) is not None:
        return True

    if local_dev_auth_bypass():
        _apply_dev_login(default_dev_user())
        return True

    if _try_restore_auth_from_cookie():
        return True

    _hide_streamlit_chrome()
    callback_error = _handle_oauth_callback()
    if callback_error:
        st.session_state["login_error"] = callback_error
    error = str(st.session_state.pop("login_error", "") or "")

    st.markdown('<p class="login-title">Agent Dungeon</p>', unsafe_allow_html=True)
    st.markdown('<p class="login-sub">闖關式 Agent Studio</p>', unsafe_allow_html=True)
    if error:
        st.error(error)

    if oauth_enabled():
        oauth = build_oauth_service()
        state = _oauth_state(oauth)
        _render_oauth_login_link("使用 Google 帳號登入", oauth.authorize_url(state))
        st.caption(f"Redirect URI：`{oauth_redirect_uri()}`")
        return False

    st.warning("未設定 Google OAuth。請編輯 `%USERPROFILE%\\.agent_dungeon\\local.env`。")
    with st.form("dev_login"):
        email = st.text_input("Gmail")
        name = st.text_input("姓名")
        if st.form_submit_button("開發模式登入", use_container_width=True):
            from agent_dungeon.auth.session import dev_login

            try:
                claims = dev_login(email, name)
            except ValueError as exc:
                st.session_state["login_error"] = str(exc)
                st.rerun()
            user = _apply_dev_login_return_user(claims)
            _complete_login(user)
    return False


def _apply_dev_login_return_user(claims: GoogleUserClaims) -> AuthUser:
    bootstrap_shared_config()
    user = set_auth_user(st.session_state, claims)
    paths = paths_for_user(user.google_sub)
    ensure_user_dirs(paths)
    ensure_user_agent_config(user.google_sub)
    write_profile(paths, email=user.email, name=user.name)
    return user


def render_logout_button() -> None:
    user = get_auth_user(st.session_state)
    if user is None:
        return
    with st.sidebar:
        st.caption(user.name)
        st.caption(user.email)
        if st.button("登出", use_container_width=True):
            from agent_dungeon.auth.session import clear_auth

            clear_auth(st.session_state)
            st.rerun()
