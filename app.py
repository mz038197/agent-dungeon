from __future__ import annotations

import streamlit as st

from auth.gate import render_login_gate, render_logout_button
from bootstrap_config import apply_config_override, bootstrap_shared_config
from cloud_paths import APP_ROOT, ensure_user_dirs, paths_for_user
from auth.session import get_auth_user
from env_loader import bootstrap_environment
from shell_ui import build_navigation_pages, inject_style

bootstrap_environment()
bootstrap_shared_config()
apply_config_override()

st.set_page_config(page_title="Agent Dungeon", page_icon="🐉", layout="wide")

if not render_login_gate():
    st.stop()

user = get_auth_user(st.session_state)
if user is not None:
    ensure_user_dirs(paths_for_user(user.google_sub))

render_logout_button()
inject_style()


def overview() -> None:
    from shell_ui import format_extra_context
    from page_shell import page_shell

    def render_main() -> str:
        st.markdown(
            """
### 歡迎來 Agent Dungeon
- 左欄：闖關練習與 Streamlit UI
- 右欄：連接 **peas-agent-core** Agent
- 進度與對話會保存在你的 Google 帳號下

從側欄進入 **Home** 開始第一關占位練習。
"""
        )
        return format_extra_context("總覽")

    page_shell(
        "Agent Dungeon",
        "登入成功 — 開始你的闖關之旅。",
        render_main,
        page_name="總覽",
    )


pages = build_navigation_pages(app_root=APP_ROOT, overview_callable=overview)
st.navigation(pages).run()
