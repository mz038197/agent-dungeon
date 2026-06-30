from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import streamlit as st

from agent_dungeon.auth.session import clear_auth, get_auth_user
from agent_dungeon.core.cloud_paths import APP_ROOT
from agent_dungeon.core.progress import DungeonProgress, ModuleStatus, agent_level_view, load_user_progress
from agent_dungeon.ui.shell_ui import dungeon_file_page, navigation_page_path, overview_page

ModuleId = Literal[
    "voice", "brain", "memory", "identity", "tools", "planning", "team"
]

MODULE_DEFS: tuple[dict[str, object], ...] = (
    {"id": "voice", "label": "Voice", "icon": "🎙️", "page": "level_pages/0_Voice.py"},
    {"id": "brain", "label": "Brain", "icon": "🧠", "page": "level_pages/1_Brain.py"},
    {"id": "memory", "label": "Memory", "icon": "📗", "page": "level_pages/2_Memory.py"},
    {"id": "identity", "label": "Identity", "icon": "🤖", "page": "level_pages/3_Identity.py"},
    {"id": "tools", "label": "Tools", "icon": "🛠️", "page": "level_pages/4_Tools.py"},
    {"id": "planning", "label": "Planning", "icon": "🗺️", "page": "level_pages/5_Planning.py"},
    {"id": "team", "label": "Team", "icon": "👥", "page": "level_pages/6_Team.py"},
)


@dataclass(frozen=True)
class ModuleNavItem:
    id: ModuleId
    label: str
    icon: str
    page: str
    status: ModuleStatus


def _module_items(progress: DungeonProgress) -> list[ModuleNavItem]:
    items: list[ModuleNavItem] = []
    for raw in MODULE_DEFS:
        module_id = str(raw["id"])
        status = progress.modules.get(module_id, ModuleStatus.LOCKED)
        items.append(
            ModuleNavItem(
                id=module_id,  # type: ignore[arg-type]
                label=str(raw["label"]),
                icon=str(raw["icon"]),
                page=str(raw["page"]),
                status=status,
            )
        )
    return items


def _status_label(status: ModuleStatus) -> str:
    if status == ModuleStatus.IN_PROGRESS:
        return "進行中"
    if status == ModuleStatus.COMPLETE:
        return "已完成"
    return "未解鎖"


def _page_exists(relative_page: str) -> bool:
    return (APP_ROOT / relative_page).is_file()


def _render_progress_card(progress: DungeonProgress) -> None:
    level, next_hint, xp, xp_to_next = agent_level_view(progress)
    xp_pct = min(xp / xp_to_next, 1.0) if xp_to_next else 0.0
    fill_pct = max(xp_pct * 100, 0.0)
    st.markdown(
        f"""
<div class="dungeon-progress-card">
  <div class="dungeon-progress-head">
    <div>
      <div class="dungeon-progress-label">你的進度</div>
      <div class="dungeon-progress-sub">Agent 等級</div>
      <div class="dungeon-progress-lv">Lv. {level}</div>
    </div>
    <div class="dungeon-progress-xp">{xp} / {xp_to_next} XP</div>
  </div>
  <div class="dungeon-progress-track">
    <div class="dungeon-progress-fill" style="width:{fill_pct:.1f}%"></div>
  </div>
  <div class="dungeon-progress-next">下一級：{html.escape(next_hint)}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_left_sidebar(*, current_module: ModuleId | None, progress: DungeonProgress) -> None:
    st.markdown(
        """
<div class="dungeon-brand">
  <span class="dungeon-brand-icon">🏰</span>
  <div>
    <div class="dungeon-brand-title">AGENT DUNGEON</div>
    <div class="dungeon-brand-sub">打造你的專屬 AI 助手！</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    if current_module is not None:
        if st.button("🏠 回到總覽", key="nav_overview", use_container_width=True):
            st.switch_page(overview_page())

    _render_progress_card(progress)

    st.markdown("#### 模組 (Modules)")
    for index, item in enumerate(_module_items(progress)):
        level_num = index + 1
        is_current = current_module == item.id
        status = item.status
        clickable = (
            status in (ModuleStatus.IN_PROGRESS, ModuleStatus.COMPLETE)
            and _page_exists(item.page)
        )
        row_class = "dungeon-module-row"
        if is_current:
            row_class += " dungeon-module-active"
        if status == ModuleStatus.LOCKED:
            row_class += " dungeon-module-locked"

        cols = st.columns([1, 3, 3])
        cols[0].markdown(f"<span class='dungeon-module-icon'>{item.icon}</span>", unsafe_allow_html=True)
        cols[1].markdown(
            f"<div class='dungeon-module-name'>{item.label} Lv.{level_num}</div>",
            unsafe_allow_html=True,
        )
        pill = _status_label(status)
        if clickable:
            with cols[2]:
                if st.button(pill, key=f"nav_module_{item.id}", use_container_width=True):
                    st.switch_page(dungeon_file_page(item.page))
        else:
            cols[2].markdown(
                f"<span class='dungeon-module-pill locked'>{pill}</span>",
                unsafe_allow_html=True,
            )

    st.markdown("#### 背包 (Inventory)")
    st.markdown(
        """
<div class="dungeon-inventory">
  <div>🎁 完成關卡可獲得獎勵！</div>
  <div class="dungeon-rewards">
    <span class="dungeon-orb exp">EXP<br><small>經驗值</small></span>
    <span class="dungeon-orb mp">MP<br><small>模組點數</small></span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    foot = st.columns(3)
    foot[0].button("🏆 排行榜", disabled=True, use_container_width=True, key="nav_leaderboard")
    foot[1].button("⭐ 成就", disabled=True, use_container_width=True, key="nav_achievements")
    with st.expander("⚙️ 設定"):
        user = get_auth_user(st.session_state)
        if user is not None:
            st.caption(user.name)
            st.caption(user.email)
        if st.button("登出", type="primary", use_container_width=True, key="dungeon_logout"):
            clear_auth(st.session_state)
            st.rerun()


def render_footer_bar(progress: DungeonProgress) -> None:
    completed = sum(
        1 for status in progress.modules.values() if status == ModuleStatus.COMPLETE
    )
    total_modules = len(MODULE_DEFS)
    cols = st.columns([3, 4, 2])
    cols[0].caption("💡 小提醒：完成 Skill Forge 三關，再進 Forge Lab 讓 Agent 開口！")
    cols[1].progress(
        completed / total_modules if total_modules else 0.0,
        text=f"冒險進度 {completed}/{total_modules}",
    )
    cols[2].caption(f"⭐ {progress.xp} EXP　🔶 {progress.mp} MP")


def load_sidebar_progress(google_sub: str) -> DungeonProgress:
    return load_user_progress(google_sub)
