from __future__ import annotations

import streamlit as st

from cloud_paths import APP_ROOT
from dungeon_shell import dungeon_shell
from page_bootstrap import init_dungeon_environment, require_dungeon_login
from shell_ui import build_navigation_pages, format_extra_context

init_dungeon_environment()

st.set_page_config(page_title="Agent Dungeon", page_icon="🐉", layout="wide")

require_dungeon_login()


def overview() -> None:
    def render_main(_progress) -> str:
        st.markdown("## 歡迎來 Agent Dungeon")
        st.markdown(
            """
- **左欄**：你的進度、模組地圖與背包
- **中欄**：關卡 Mission、Skill Forge、Forge Lab
- **右欄**：Agent 面板（可選啟用 LLM 對話）

從左欄 **Voice 模組（進行中）** 進入第 1 關開始冒險。
"""
        )
        return format_extra_context("總覽")

    dungeon_shell(render_main, current_module=None, page_name="總覽")


pages = build_navigation_pages(app_root=APP_ROOT, overview_callable=overview)
st.navigation(pages, position="hidden").run()
