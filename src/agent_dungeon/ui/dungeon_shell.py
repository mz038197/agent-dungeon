from __future__ import annotations

from collections.abc import Callable

import streamlit as st
import streamlit.components.v1 as components

from agent_dungeon.agent.agent_column import render_agent_column
from agent_dungeon.auth.session import get_auth_user
from agent_dungeon.core.cloud_paths import paths_for_user
from agent_dungeon.core.progress import DungeonProgress, load_user_progress
from agent_dungeon.ui.sidebar_nav import ModuleId, render_footer_bar, render_left_sidebar
from agent_dungeon.ui.shell_ui import (
    inject_css_block,
    multimodal_chatinput_light_theme_js,
    shell_base_css,
    component_pointer_pass_through_js,
)


_DUNGEON_INNER_CSS = """
  /* 參考 mockup：左／footer 深藍、中欄淺灰、右欄米色 */
  [data-testid="stAppViewContainer"] {
    background-color: #e2e8f0 !important;
  }
  [data-testid="stSidebar"] { display: none !important; }
  [data-testid="stSidebarCollapsedControl"] { display: none !important; }
  .block-container,
  [data-testid="stMainBlockContainer"] {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    margin-bottom: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    max-width: 100% !important;
  }
  #dungeon-shell-anchor, #dungeon-footer-anchor,
  #dungeon-css-anchor, #dungeon-paint-anchor { display: none; }
  [data-testid="stElementContainer"]:has(#dungeon-shell-anchor),
  [data-testid="stElementContainer"]:has(#dungeon-footer-anchor),
  [data-testid="stElementContainer"]:has(#dungeon-css-anchor),
  [data-testid="stElementContainer"]:has(#dungeon-paint-anchor) {
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
    max-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
    border: none !important;
  }

  /* 主容器與 header 零上距（三欄貼頂；Streamlit 1.58 stAppHeader） */
  header.stAppHeader,
  [data-testid="stAppHeader"] {
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
    max-height: 0 !important;
    overflow: hidden !important;
    padding: 0 !important;
    margin: 0 !important;
  }
  [data-testid="stAppViewBlockContainer"],
  .stAppViewBlockContainer,
  section.stMain .block-container {
    padding-top: 0 !important;
    margin-top: 0 !important;
  }
  [data-testid="stAppViewContainer"] .main .block-container,
  [data-testid="stAppViewContainer"] > section.main > div {
    padding-top: 0 !important;
    margin-top: 0 !important;
  }
  [data-testid="stHeader"] {
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
    overflow: hidden !important;
  }
  [data-testid="stElementContainer"]:has(#dungeon-shell-anchor) {
    margin-top: 0 !important;
    padding-top: 0 !important;
  }

  /* Shell 三欄：左貼邊、三欄上貼頂、中欄吃滿釋出空間 */
  [data-testid="stElementContainer"]:has(#dungeon-shell-anchor)
    + [data-testid="stLayoutWrapper"] {
    max-width: none !important;
    width: 100% !important;
    margin-top: 0 !important;
    margin-bottom: 0 !important;
  }
  [data-testid="stElementContainer"]:has(#dungeon-shell-anchor)
    + [data-testid="stLayoutWrapper"]
    > [data-testid="stHorizontalBlock"] {
    width: 100% !important;
    max-width: none !important;
    margin-top: 0 !important;
  }

  /* Shell 三欄底色 */
  [data-testid="stElementContainer"]:has(#dungeon-shell-anchor)
    + [data-testid="stLayoutWrapper"]
    > [data-testid="stHorizontalBlock"]
    > [data-testid="stColumn"]:nth-child(1) {
    background-color: #0b1120 !important;
    color: #f8fafc !important;
    border-radius: 0 !important;
    padding: 0.65rem 0.85rem !important;
  }
  [data-testid="stElementContainer"]:has(#dungeon-shell-anchor)
    + [data-testid="stLayoutWrapper"]
    > [data-testid="stHorizontalBlock"]
    > [data-testid="stColumn"]:nth-child(2) {
    background-color: #f8fafc !important;
    color: #0f172a !important;
    border-radius: 12px;
    padding: 0.65rem 0.85rem !important;
  }
  [data-testid="stElementContainer"]:has(#dungeon-shell-anchor)
    + [data-testid="stLayoutWrapper"]
    > [data-testid="stHorizontalBlock"]
    > [data-testid="stColumn"]:nth-child(3) {
    background-color: #fff7ed !important;
    color: #0f172a !important;
    border-radius: 12px;
    padding: 0.65rem 0.85rem !important;
  }

  /* Main 垂直區塊：消除 shell 與 footer 之間 Streamlit 預設 16px gap */
  [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {
    gap: 0 !important;
    row-gap: 0 !important;
  }

  /* Footer 深藍底 */
  [data-testid="stElementContainer"]:has(#dungeon-footer-anchor)
    + [data-testid="stLayoutWrapper"] {
    background-color: #0b1120 !important;
    border-radius: 0 !important;
    padding: 0.55rem 1rem !important;
    margin-top: 0 !important;
    margin-bottom: 0 !important;
  }
  [data-testid="stElementContainer"]:has(#dungeon-footer-anchor)
    + [data-testid="stLayoutWrapper"] [data-testid="stCaptionContainer"] {
    color: #94a3b8 !important;
  }

  .dungeon-brand {
    display: flex; gap: 0.65rem; align-items: center;
    padding: 0.5rem 0 1rem;
  }
  .dungeon-brand-icon { font-size: 1.5rem; }
  .dungeon-brand-title { font-weight: 800; font-size: 1rem; letter-spacing: 0.04em; color: #f8fafc; }
  .dungeon-brand-sub { color: rgba(248,250,252,0.65); font-size: 0.78rem; }
  .dungeon-module-row { margin-bottom: 0.15rem; }
  .dungeon-module-name { font-size: 0.9rem; font-weight: 600; color: #f1f5f9; }
  .dungeon-module-pill {
    display: inline-block; padding: 0.15rem 0.45rem; border-radius: 999px;
    font-size: 0.72rem; background: rgba(139,92,246,0.35); color: #ddd6fe;
    white-space: nowrap;
  }
  [data-testid="stColumn"] [data-testid="stButton"] button {
    white-space: nowrap;
    font-size: 0.72rem;
  }
  .dungeon-col-sidebar [data-testid="stButton"] button {
    color: #0f172a !important;
    background-color: #f1f5f9 !important;
    border: 1px solid rgba(148, 163, 184, 0.45) !important;
  }
  .dungeon-col-sidebar [data-testid="stButton"] button:hover:not(:disabled) {
    color: #0f172a !important;
    background-color: #e2e8f0 !important;
  }
  .dungeon-col-sidebar [data-testid="stButton"] button:disabled {
    color: #64748b !important;
    background-color: rgba(241, 245, 249, 0.5) !important;
  }
  .dungeon-col-sidebar .dungeon-nav-anchor {
    display: inline-flex !important;
    align-items: center;
    justify-content: center;
    width: 100%;
    white-space: nowrap;
    font-size: 0.72rem !important;
    font-weight: 600;
    color: #0f172a !important;
    background-color: #f1f5f9 !important;
    border: 1px solid rgba(148, 163, 184, 0.45) !important;
    border-radius: 0.5rem !important;
    padding: 0.35rem 0.5rem !important;
    text-decoration: none !important;
    box-sizing: border-box;
    min-height: 2.5rem;
  }
  .dungeon-col-sidebar .dungeon-nav-anchor:hover {
    color: #0f172a !important;
    background-color: #e2e8f0 !important;
    border-color: rgba(148, 163, 184, 0.55) !important;
    text-decoration: none !important;
  }
  .dungeon-col-sidebar [data-testid="stLinkButton"],
  .dungeon-col-sidebar [data-testid="stPageLink"] {
    width: 100%;
  }
  .dungeon-col-sidebar [data-testid="stLinkButton"] a,
  .dungeon-col-sidebar [data-testid="stPageLink"] a {
    display: inline-flex !important;
    align-items: center;
    justify-content: center;
    width: 100%;
    white-space: nowrap;
    font-size: 0.72rem !important;
    color: #0f172a !important;
    background-color: #f1f5f9 !important;
    border: 1px solid rgba(148, 163, 184, 0.45) !important;
    border-radius: 0.5rem !important;
    padding: 0.35rem 0.5rem !important;
    text-decoration: none !important;
    box-sizing: border-box;
  }
  .dungeon-col-sidebar [data-testid="stLinkButton"] a:hover,
  .dungeon-col-sidebar [data-testid="stPageLink"] a:hover {
    color: #0f172a !important;
    background-color: #e2e8f0 !important;
    border-color: rgba(148, 163, 184, 0.55) !important;
  }
  [data-testid="stElementContainer"]:has(#dungeon-shell-anchor)
    + [data-testid="stLayoutWrapper"]
    > [data-testid="stHorizontalBlock"]
    > [data-testid="stColumn"]:nth-child(1) {
    position: relative;
    z-index: 3;
  }
  /* 中欄／右欄：Streamlit 1.58 次要按鈕改淺色底 + 可見框線 */
  .dungeon-col-center button[data-testid="stBaseButton-secondary"],
  .dungeon-col-agent button[data-testid="stBaseButton-secondary"] {
    color: #0f172a !important;
    background-color: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
  }
  .dungeon-col-center button[data-testid="stBaseButton-secondary"]:hover:not(:disabled),
  .dungeon-col-agent button[data-testid="stBaseButton-secondary"]:hover:not(:disabled) {
    color: #0f172a !important;
    background-color: #f8fafc !important;
    border-color: #cbd5e1 !important;
  }
  .dungeon-col-center button[data-testid="stBaseButton-secondary"]:disabled,
  .dungeon-col-agent button[data-testid="stBaseButton-secondary"]:disabled {
    color: #94a3b8 !important;
    background-color: #f1f5f9 !important;
    border-color: #e2e8f0 !important;
  }
  /* 中欄／右欄：primary 按鈕靛紫 */
  .dungeon-col-center button[data-testid="stBaseButton-primary"],
  .dungeon-col-agent button[data-testid="stBaseButton-primary"] {
    color: #ffffff !important;
    background-color: #6366f1 !important;
    border: none !important;
    box-shadow: none !important;
  }
  .dungeon-col-center button[data-testid="stBaseButton-primary"]:hover:not(:disabled),
  .dungeon-col-agent button[data-testid="stBaseButton-primary"]:hover:not(:disabled) {
    color: #ffffff !important;
    background-color: #4f46e5 !important;
    border: none !important;
  }
  .dungeon-col-center button[data-testid="stBaseButton-primary"]:disabled,
  .dungeon-col-agent button[data-testid="stBaseButton-primary"]:disabled {
    color: #64748b !important;
    background-color: #cbd5e1 !important;
    border: none !important;
  }
  .dungeon-col-center [data-testid="stIconMaterial"],
  .dungeon-col-agent [data-testid="stIconMaterial"] {
    color: #0f172a !important;
    fill: currentColor !important;
  }
  .dungeon-module-pill.locked {
    background: rgba(148,163,184,0.2); color: rgba(226,232,240,0.9);
  }
  .dungeon-inventory {
    border: 1px solid rgba(148,163,184,0.25); border-radius: 12px;
    padding: 0.75rem; margin: 0.5rem 0 1rem; background: rgba(15,23,42,0.55);
  }
  .dungeon-rewards { display: flex; gap: 0.75rem; margin-top: 0.5rem; }
  .dungeon-orb {
    display: inline-flex; flex-direction: column; align-items: center;
    width: 3.5rem; height: 3.5rem; border-radius: 999px; font-size: 0.7rem;
    justify-content: center; font-weight: 700;
  }
  .dungeon-orb.exp { background: radial-gradient(circle, #38bdf8, #1d4ed8); }
  .dungeon-orb.mp { background: radial-gradient(circle, #fbbf24, #ea580c); }
  .dungeon-progress-card {
    background: #12121a;
    border-radius: 12px;
    padding: 0.85rem 1rem;
    margin: 0.25rem 0 1rem;
    border: 1px solid rgba(157, 139, 255, 0.12);
  }
  .dungeon-progress-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 0.75rem;
    margin-bottom: 0.55rem;
  }
  .dungeon-progress-label {
    font-size: 0.72rem;
    color: rgba(248, 250, 252, 0.75);
    margin-bottom: 0.15rem;
  }
  .dungeon-progress-sub {
    font-size: 0.82rem;
    color: #f8fafc;
    margin-bottom: 0.2rem;
  }
  .dungeon-progress-lv {
    font-size: 1.85rem;
    font-weight: 800;
    line-height: 1.1;
    color: #ffffff;
    letter-spacing: 0.02em;
  }
  .dungeon-progress-xp {
    font-size: 0.78rem;
    color: #a0a0a0;
    white-space: nowrap;
    padding-top: 1.35rem;
  }
  .dungeon-progress-track {
    height: 10px;
    border-radius: 999px;
    background: #3b3b4f;
    overflow: hidden;
    margin-bottom: 0.55rem;
  }
  .dungeon-progress-fill {
    height: 100%;
    border-radius: 999px;
    background: #9d8bff;
    box-shadow: 0 0 10px rgba(157, 139, 255, 0.45);
    transition: width 0.25s ease;
  }
  .dungeon-progress-next {
    font-size: 0.78rem;
    color: #94a3b8;
    line-height: 1.35;
  }
  .dungeon-level-tag {
    display: inline-block; padding: 0.15rem 0.55rem; border-radius: 999px;
    background: rgba(59,130,246,0.15); color: #2563eb; font-size: 0.75rem;
    margin-bottom: 0.15rem;
  }
  .dungeon-col-center [data-testid="stMarkdownContainer"] h2 {
    margin-top: 0 !important;
    margin-bottom: 0.25rem !important;
    padding-top: 0 !important;
  }
  .dungeon-col-center [data-testid="stElementContainer"]:has(.dungeon-section-heading) {
    margin-top: 0.35rem !important;
    margin-bottom: 0 !important;
  }
  .dungeon-col-center [data-testid="stElementContainer"]:has(.dungeon-level-tag) {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
  }
  .dungeon-col-center hr {
    margin: 0.35rem 0 !important;
  }
  .dungeon-section {
    border: 1px solid rgba(148,163,184,0.18); border-radius: 14px;
    padding: 0.9rem 1rem; margin-bottom: 0.85rem;
    background: rgba(255,255,255,0.03);
  }
  .dungeon-section h4 { margin-top: 0; margin-bottom: 0.35rem; }
  .voice-module-online { color: #16a34a; font-weight: 700; }
  .voice-module-offline { color: #dc2626; font-weight: 700; }

  /* 編號區段標題 */
  .dungeon-section-heading {
    display: flex; align-items: center; gap: 0.5rem;
    margin: 0.15rem 0 0.35rem;
  }
  .dungeon-section-badge {
    display: inline-flex; align-items: center; justify-content: center;
    width: 1.65rem; height: 1.65rem; border-radius: 999px;
    font-weight: 800; font-size: 0.85rem; color: #ffffff; flex-shrink: 0;
  }
  .dungeon-section-heading--purple .dungeon-section-badge { background: #6366f1; }
  .dungeon-section-heading--purple .dungeon-section-title { color: #6366f1; }
  .dungeon-section-heading--blue .dungeon-section-badge { background: #2563eb; }
  .dungeon-section-heading--blue .dungeon-section-title { color: #2563eb; }
  .dungeon-section-heading--green .dungeon-section-badge { background: #16a34a; }
  .dungeon-section-heading--green .dungeon-section-title { color: #16a34a; }
  .dungeon-section-title {
    font-weight: 800; font-size: 1.05rem; letter-spacing: 0.02em;
  }

  /* MISSION COMPLETE 橫幅 */
  .mission-complete-banner-v2 {
    display: flex; align-items: center; gap: 0.75rem;
    background: #fffbeb; border: 1px solid #fde68a; border-radius: 12px;
    padding: 0.85rem 1rem;
  }
  .mission-complete-trophy { font-size: 1.75rem; flex-shrink: 0; }
  .mission-complete-title {
    font-weight: 800; font-size: 1rem; color: #d97706;
    letter-spacing: 0.03em;
  }
  .mission-complete-msg {
    font-size: 0.85rem; color: #334155; margin-top: 0.15rem; line-height: 1.4;
  }
  .mission-complete-next {
    text-align: center;
  }
  .mission-complete-next-label {
    font-size: 0.78rem; color: #334155; margin-bottom: 0.35rem;
  }
  .mission-complete-next-icon {
    display: inline-flex; align-items: center; justify-content: center;
    width: 2.5rem; height: 2.5rem; border-radius: 999px;
    background: #f3e8ff; border: 1px solid #c4b5fd;
    font-size: 1.25rem;
  }

  /* 延伸技能面板（中欄通關後橫向 bar） */
  .skills-panel-bar {
    display: flex; align-items: center; justify-content: space-between;
    gap: 1rem; flex-wrap: wrap;
    background: #f5f3ff; border: 1px solid #ddd6fe; border-radius: 12px;
    padding: 0.75rem 1rem; margin-top: 0.5rem;
  }
  .skills-panel-copy {
    display: flex; align-items: flex-start; gap: 0.5rem;
    flex: 1 1 220px; min-width: 0;
  }
  .skills-panel-icon { font-size: 1.25rem; flex-shrink: 0; line-height: 1.2; }
  .skills-panel-title {
    font-weight: 800; font-size: 0.92rem; color: #5b21b6;
    letter-spacing: 0.01em;
  }
  .skills-panel-subtitle {
    font-size: 0.78rem; color: #64748b; margin-top: 0.1rem; line-height: 1.35;
  }
  .skills-panel-badges {
    display: flex; flex-wrap: wrap; gap: 0.45rem;
    justify-content: flex-end; flex: 1 1 280px;
  }
  .skill-badge {
    display: inline-flex; align-items: center; gap: 0.35rem;
    border: 1px solid #e2e8f0; border-radius: 10px;
    padding: 0.35rem 0.55rem; font-size: 0.75rem;
    background: #ffffff; white-space: nowrap;
  }
  .skill-badge.unlocked {
    color: #0f172a; border-color: rgba(139, 92, 246, 0.45);
  }
  .skill-badge.locked { color: #94a3b8; }
  .skill-badge-icon { font-size: 0.85rem; line-height: 1; flex-shrink: 0; }
  .skill-badge-label { line-height: 1.2; }
  .skill-badge-lock {
    font-size: 0.72rem; line-height: 1; margin-left: 0.15rem; flex-shrink: 0;
  }

  /* Mission 三卡 demo 與外框留白 */
  .mission-demo-host {
    display: block;
    margin-top: 0.35rem;
  }

  /* Mission Demo 迷你對話氣泡 */
  .mission-demo {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.55rem 0.65rem;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }
  .mission-demo-caption {
    font-size: 0.72rem;
    color: #64748b;
    margin-bottom: 0.1rem;
  }
  .mission-demo-bubble {
    border-radius: 10px;
    padding: 0.45rem 0.55rem;
    font-size: 0.82rem;
    line-height: 1.35;
    color: #0f172a;
  }
  .mission-demo-user {
    background: #e2e8f0;
    align-self: flex-end;
    max-width: 88%;
  }
  .mission-demo-agent {
    background: #fff7ed;
    border: 1px solid #fed7aa;
    align-self: flex-start;
    max-width: 95%;
  }
  .mission-demo-role {
    display: block;
    font-size: 0.68rem;
    font-weight: 700;
    color: #64748b;
    margin-bottom: 0.15rem;
  }
  .mission-demo-text {
    display: block;
  }

  /* 自訂 hint（取代 st.info） */
  .dungeon-hint {
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-left: 3px solid #6366f1;
    border-radius: 10px;
    padding: 0.55rem 0.75rem;
    font-size: 0.88rem;
    color: #334155;
    margin-bottom: 0.75rem;
  }

  .skill-forge-summary {
    font-size: 0.88rem;
    color: #334155;
    margin: 0.25rem 0 0.5rem;
  }

  /* 中欄 */
  .dungeon-col-center [data-testid="stVerticalBlock"] {
    background-color: transparent !important;
  }
  /* Streamlit 1.58+：border 容器為 stLayoutWrapper > stVerticalBlock */
  .dungeon-col-center [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"] {
    background-color: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px;
  }
  .dungeon-col-center [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"]:has(.dungeon-forge-lab-band) {
    background-color: #f1f5f9 !important;
    border: 1px solid #e2e8f0 !important;
  }
  .dungeon-col-center [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"]:has(.skill-forge-band) {
    background-color: #f1f5f9 !important;
    border: 1px solid #e2e8f0 !important;
  }
  .dungeon-col-center [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"]:has(.skills-panel-bar) {
    border: 1px solid #c4b5fd !important;
  }
  .dungeon-col-center [data-testid="stAlert"] {
    background-color: #ffffff !important;
    border-color: #e2e8f0 !important;
    color: #0f172a !important;
  }
  .dungeon-col-center [data-testid="stTextArea"] textarea,
  .dungeon-col-center [data-testid="stTextArea"] textarea:disabled {
    background-color: #0f172a !important;
    color: #e2e8f0 !important;
    -webkit-text-fill-color: #e2e8f0 !important;
    caret-color: #e2e8f0 !important;
    border: 1px solid #334155 !important;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 0.85rem;
  }
  .dungeon-col-center [data-testid="stCode"] pre,
  .dungeon-col-center [data-testid="stCode"] code {
    background: #1e293b !important;
    border: 1px solid #334155;
    border-radius: 8px;
    color: #e2e8f0 !important;
  }
  .dungeon-col-center [data-testid="stCode"] pre span {
    color: #e2e8f0 !important;
    background-color: transparent !important;
  }
  .dungeon-col-center [data-testid="stMarkdownContainer"] p,
  .dungeon-col-center [data-testid="stMarkdownContainer"] li,
  .dungeon-col-center [data-testid="stMarkdownContainer"] h1,
  .dungeon-col-center [data-testid="stMarkdownContainer"] h2,
  .dungeon-col-center [data-testid="stMarkdownContainer"] h3,
  .dungeon-col-center [data-testid="stMarkdownContainer"] h4 {
    color: #0f172a !important;
  }
  .dungeon-col-center [data-testid="stCaptionContainer"] {
    color: #64748b !important;
  }

  /* 右欄 agent.py 預覽 */
  .dungeon-col-agent [data-testid="stCode"] {
    max-height: 180px; overflow: auto;
  }
  .dungeon-col-agent [data-testid="stCode"] pre,
  .dungeon-col-agent [data-testid="stCode"] code {
    background: #1e293b !important;
    border: 1px solid #334155;
    border-radius: 8px;
    color: #e2e8f0 !important;
  }
  .dungeon-col-agent [data-testid="stCode"] pre span {
    color: #e2e8f0 !important;
    background-color: transparent !important;
  }

  /* 右欄 Agent */
  .dungeon-col-agent [data-testid="stVerticalBlock"] {
    background-color: transparent !important;
  }
  .dungeon-col-agent [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 10px;
  }
  .dungeon-col-agent .studio-agent-title-text {
    color: #0f172a !important;
  }
  .dungeon-col-agent [data-testid="stMarkdownContainer"] p,
  .dungeon-col-agent [data-testid="stMarkdownContainer"] h1,
  .dungeon-col-agent [data-testid="stMarkdownContainer"] h2,
  .dungeon-col-agent [data-testid="stMarkdownContainer"] h3,
  .dungeon-col-agent [data-testid="stMarkdownContainer"] h4,
  .dungeon-col-agent [data-testid="stMarkdownContainer"] li,
  .dungeon-col-agent [data-testid="stMarkdownContainer"] ul,
  .dungeon-col-agent [data-testid="stMarkdownContainer"] ol,
  .dungeon-col-agent [data-testid="stMarkdownContainer"] strong,
  .dungeon-col-agent [data-testid="stMarkdownContainer"] em,
  .dungeon-col-agent [data-testid="stMarkdownContainer"] blockquote {
    color: #0f172a !important;
  }
  .dungeon-col-agent [data-testid="stMarkdownContainer"] code {
    color: #0f172a !important;
    background-color: #f1f5f9 !important;
  }
  /* 對話氣泡 */
  .dungeon-col-agent [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background-color: #f1f5f9 !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
  }
  .dungeon-col-agent [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
    background-color: transparent !important;
  }
  .dungeon-col-agent [data-testid="stChatMessage"] [data-testid="stExpander"] summary,
  .dungeon-col-agent [data-testid="stChatMessage"] [data-testid="stExpanderDetails"] {
    background-color: #ffffff !important;
    color: #0f172a !important;
    border-color: #e2e8f0 !important;
  }
  .dungeon-col-agent [data-testid="stCaptionContainer"] {
    color: #64748b !important;
  }
  .dungeon-col-agent iframe[title*="multimodal"],
  .dungeon-col-agent iframe[src*="st_multimodal_chatinput"] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
    pointer-events: auto !important;
  }
  /* 右欄不應出現延伸技能面板（舊版 agent_column 殘留時隱藏） */
  .dungeon-col-agent .skills-panel-bar {
    display: none !important;
  }

  /* 右欄表單：Streamlit 1.58 預設深色輸入框改淺色 */
  .dungeon-col-agent [data-testid="stWidgetLabel"],
  .dungeon-col-agent [data-testid="stWidgetLabel"] p,
  .dungeon-col-agent [data-testid="stWidgetLabel"] [data-testid="stMarkdownContainer"] p {
    color: #0f172a !important;
  }
  .dungeon-col-agent [data-testid="stSelectbox"] [data-baseweb="select"],
  .dungeon-col-agent [data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background-color: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    color: #0f172a !important;
  }
  .dungeon-col-agent [data-testid="stSelectbox"] [data-baseweb="select"] svg {
    fill: #64748b !important;
  }
  .dungeon-col-agent [data-testid="stTextAreaRootElement"],
  .dungeon-col-agent [data-testid="stTextArea"] textarea {
    background-color: #ffffff !important;
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
    caret-color: #0f172a !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
  }
  .dungeon-col-agent [data-testid="stTextArea"] textarea:disabled {
    background-color: #f1f5f9 !important;
    color: #64748b !important;
    -webkit-text-fill-color: #64748b !important;
  }
  .dungeon-col-agent [data-testid="stNumberInputContainer"] {
    background-color: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
  }
  .dungeon-col-agent [data-testid="stNumberInputField"] {
    background-color: #ffffff !important;
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
    border: none !important;
  }
  .dungeon-col-agent [data-testid="stNumberInputField"]:disabled {
    background-color: #f1f5f9 !important;
    color: #64748b !important;
    -webkit-text-fill-color: #64748b !important;
  }
  .dungeon-col-agent [data-testid="stNumberInputStepDown"] button,
  .dungeon-col-agent [data-testid="stNumberInputStepUp"] button {
    background-color: #f8fafc !important;
    color: #0f172a !important;
    border: 1px solid #e2e8f0 !important;
  }
  .dungeon-col-agent [data-testid="stCheckbox"] label > span:first-of-type {
    background-color: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
  }
  .dungeon-col-agent [data-testid="stExpander"] summary {
    background-color: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
  }
  .dungeon-col-agent [data-testid="stExpanderDetails"] {
    background-color: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-top: none !important;
    border-radius: 0 0 8px 8px !important;
    padding: 0.35rem 0.65rem 0.65rem !important;
  }
  .dungeon-col-agent [data-testid="stAlert"] {
    background-color: #ffffff !important;
    border-color: #e2e8f0 !important;
    color: #0f172a !important;
  }

  /* 左欄 sidebar 文字 */
  .dungeon-col-sidebar [data-testid="stMarkdownContainer"] h4 {
    color: #f8fafc !important;
  }
  .dungeon-col-sidebar [data-testid="stCaptionContainer"] {
    color: #94a3b8 !important;
  }
"""


def _dungeon_app_css() -> str:
    return shell_base_css() + _DUNGEON_INNER_CSS


_LIGHT_COLUMN_PAINT = """
<script>
(function () {
  __COMPONENT_POINTER_PASS_THROUGH_JS__

  const host = window.parent;
  if (!host) {
    return;
  }

  const iframe = window.frameElement;
  const paintContainer = iframe?.closest('[data-testid="stElementContainer"]');
  if (paintContainer && !paintContainer.querySelector("#dungeon-paint-anchor")) {
    const marker = host.document.createElement("span");
    marker.id = "dungeon-paint-anchor";
    marker.hidden = true;
    paintContainer.appendChild(marker);
  }

  function collapseElementContainer(node) {
    node.style.display = "none";
    node.style.height = "0px";
    node.style.minHeight = "0px";
    node.style.maxHeight = "0px";
    node.style.margin = "0px";
    node.style.padding = "0px";
    node.style.overflow = "hidden";
    node.style.border = "none";
  }

  function isMarkerContainer(node) {
    return (
      node.querySelector("#dungeon-shell-anchor")
      || node.querySelector("#dungeon-footer-anchor")
      || node.querySelector("#dungeon-css-anchor")
      || node.querySelector("#dungeon-paint-anchor")
    );
  }

  function shellColumns(doc) {
    const anchor = doc.getElementById("dungeon-shell-anchor");
    if (!anchor) {
      return null;
    }
    const anchorContainer = anchor.closest('[data-testid="stElementContainer"]');
    const layoutWrapper = anchorContainer?.nextElementSibling;
    if (!layoutWrapper) {
      return null;
    }
    const row = layoutWrapper.querySelector('[data-testid="stHorizontalBlock"]');
    if (!row) {
      return null;
    }
    const cols = row.querySelectorAll(':scope > [data-testid="stColumn"]');
    return cols.length >= 3 ? cols : null;
  }

  function paintShellColumns() {
    const doc = host.document;
    const cols = shellColumns(doc);
    if (!cols) {
      return;
    }
    cols[0].classList.add("dungeon-col-sidebar");
    cols[1].classList.add("dungeon-col-center");
    cols[2].classList.add("dungeon-col-agent");
    const row = cols[0].parentElement;
    const layoutWrapper = row?.parentElement;
    row?.classList.add("dungeon-shell-row");
    layoutWrapper?.classList.add("dungeon-shell-layout");
  }

  function shellColumnsRow(doc) {
    const anchor = doc.getElementById("dungeon-shell-anchor");
    if (!anchor) {
      return null;
    }
    const layout = anchor.closest('[data-testid="stElementContainer"]')
      ?.nextElementSibling;
    if (!layout || layout.getAttribute("data-testid") !== "stLayoutWrapper") {
      return null;
    }
    return layout.querySelector('[data-testid="stHorizontalBlock"]');
  }

  function footerLayoutWrapper(doc) {
    const anchor = doc.getElementById("dungeon-footer-anchor");
    if (!anchor) {
      return null;
    }
    const layout = anchor.closest('[data-testid="stElementContainer"]')
      ?.nextElementSibling;
    if (!layout || layout.getAttribute("data-testid") !== "stLayoutWrapper") {
      return null;
    }
    return layout;
  }

  function flushShellToTop(doc) {
    const headerSelectors = [
      "header.stAppHeader",
      '[data-testid="stAppHeader"]',
      '[data-testid="stHeader"]',
      '[data-testid="stToolbar"]',
      '[data-testid="stDecoration"]',
    ];
    headerSelectors.forEach((selector) => {
      doc.querySelectorAll(selector).forEach((node) => {
        node.style.display = "none";
        node.style.position = "absolute";
        node.style.width = "0px";
        node.style.height = "0px";
        node.style.minHeight = "0px";
        node.style.maxHeight = "0px";
        node.style.padding = "0px";
        node.style.margin = "0px";
        node.style.overflow = "hidden";
      });
    });

    const padSelectors = [
      '[data-testid="stAppViewBlockContainer"]',
      '[data-testid="stMainBlockContainer"]',
      '[data-testid="stAppViewContainer"] > section',
      '[data-testid="stVerticalBlockBorderWrapper"]',
      "section.stMain",
      "section.main",
      ".stApp",
      ".block-container",
    ];
    padSelectors.forEach((selector) => {
      doc.querySelectorAll(selector).forEach((node) => {
        node.style.paddingTop = "0px";
        node.style.marginTop = "0px";
      });
    });

    doc.querySelectorAll('[data-testid="stElementContainer"]').forEach((node) => {
      if (isMarkerContainer(node)) {
        collapseElementContainer(node);
      }
    });

    const shellRow = shellColumnsRow(doc);
    const main = doc.querySelector('[data-testid="stMainBlockContainer"]');
    const viewBlock = doc.querySelector('[data-testid="stAppViewBlockContainer"]');
    if (!shellRow || !main) {
      return false;
    }

    const top = Math.round(shellRow.getBoundingClientRect().top);
    if (top > 0) {
      main.classList.add("dungeon-shell-flush");
      main.style.setProperty("--dungeon-shell-offset", `${top}px`);
      main.style.marginTop = `-${top}px`;
      if (viewBlock) {
        viewBlock.style.paddingTop = "0px";
        viewBlock.style.marginTop = `-${top}px`;
      }
      return false;
    }

    main.classList.remove("dungeon-shell-flush");
    main.style.removeProperty("--dungeon-shell-offset");
    main.style.marginTop = "0px";
    if (viewBlock) {
      viewBlock.style.marginTop = "0px";
    }
    return true;
  }

  function flushShellToBottom(doc) {
    const padSelectors = [
      '[data-testid="stAppViewBlockContainer"]',
      '[data-testid="stMainBlockContainer"]',
      "section.stMain",
      "section.main",
      ".stApp",
      ".block-container",
    ];
    padSelectors.forEach((selector) => {
      doc.querySelectorAll(selector).forEach((node) => {
        node.style.paddingBottom = "0px";
        node.style.marginBottom = "0px";
      });
    });

    doc.querySelectorAll(
      '[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"]'
    ).forEach((node) => {
      node.style.gap = "0px";
      node.style.rowGap = "0px";
    });

    const footerLayout = footerLayoutWrapper(doc);
    if (footerLayout) {
      footerLayout.style.borderRadius = "0px";
      footerLayout.style.marginTop = "0px";
    }

    doc.querySelectorAll('[data-testid="stElementContainer"]').forEach((node) => {
      if (isMarkerContainer(node)) {
        collapseElementContainer(node);
      }
    });

    const footerContainer = doc.getElementById("dungeon-footer-anchor")
      ?.closest('[data-testid="stElementContainer"]');
    let sibling = footerLayout?.nextElementSibling;
    while (sibling) {
      if (sibling.matches('[data-testid="stElementContainer"]')) {
        collapseElementContainer(sibling);
      }
      sibling = sibling.nextElementSibling;
    }

    const main = doc.querySelector('[data-testid="stMainBlockContainer"]');
    const viewBlock = doc.querySelector('[data-testid="stAppViewBlockContainer"]');
    if (!main || !footerLayout) {
      return false;
    }

    const footerBottom = Math.round(footerLayout.getBoundingClientRect().bottom);
    const mainBottom = Math.round(main.getBoundingClientRect().bottom);
    const excess = mainBottom - footerBottom;
    if (excess > 0) {
      main.classList.add("dungeon-shell-flush-bottom");
      main.style.setProperty("--dungeon-shell-bottom-offset", `${excess}px`);
      main.style.paddingBottom = "0px";
      if (viewBlock) {
        viewBlock.classList.add("dungeon-shell-flush-bottom");
        viewBlock.style.setProperty("--dungeon-shell-bottom-offset", `${excess}px`);
        viewBlock.style.paddingBottom = "0px";
      }
      if (footerContainer) {
        footerContainer.style.marginBottom = "0px";
        footerContainer.style.paddingBottom = "0px";
      }
      return false;
    }

    main.classList.remove("dungeon-shell-flush-bottom");
    main.style.removeProperty("--dungeon-shell-bottom-offset");
    if (viewBlock) {
      viewBlock.classList.remove("dungeon-shell-flush-bottom");
      viewBlock.style.removeProperty("--dungeon-shell-bottom-offset");
    }
    return true;
  }

  __MULTIMODAL_PATCH_JS__

  let columnsPainted = false;

  function paintAll() {
    const topOk = flushShellToTop(host.document);
    const bottomOk = flushShellToBottom(host.document);
    if (!columnsPainted) {
      paintShellColumns();
      columnsPainted = !!shellColumns(host.document);
    }
    patchMultimodalChatinputIframes(host.document);
    return topOk && bottomOk && columnsPainted;
  }

  function tryPaint(attempt) {
    const done = paintAll();
    if (!done && attempt > 0) {
      host.requestAnimationFrame(() => tryPaint(attempt - 1));
    }
  }

  tryPaint(20);

  const mainBlock = host.document.querySelector('[data-testid="stMainBlockContainer"]');
  if (mainBlock && !host.__dungeonShellLayoutObserver) {
    host.__dungeonShellLayoutObserver = true;
    let pending = 0;
    new MutationObserver(() => {
      if (pending) {
        return;
      }
      pending = host.requestAnimationFrame(() => {
        pending = 0;
        flushShellToTop(host.document);
        flushShellToBottom(host.document);
      });
    }).observe(mainBlock, { childList: true, subtree: true, attributes: true });
  }
})();
</script>
"""


def _paint_light_columns() -> None:
    script = _LIGHT_COLUMN_PAINT.replace(
        "__COMPONENT_POINTER_PASS_THROUGH_JS__",
        component_pointer_pass_through_js(),
    )
    script = script.replace("__MULTIMODAL_PATCH_JS__", multimodal_chatinput_light_theme_js())
    components.html(script, height=0)


def _current_user_progress() -> DungeonProgress | None:
    user = get_auth_user(st.session_state)
    if user is None:
        return None
    return load_user_progress(user.google_sub)


def dungeon_shell(
    render_center: Callable[[DungeonProgress], str | None],
    *,
    current_module: ModuleId | None = None,
    page_name: str = "",
) -> None:
    progress = _current_user_progress()
    if progress is None:
        st.warning("請先登入。")
        return

    inject_css_block(_dungeon_app_css())
    st.markdown('<div id="dungeon-shell-anchor"></div>', unsafe_allow_html=True)
    left, center, right = st.columns([2, 6, 2], gap="small")

    with left:
        render_left_sidebar(current_module=current_module, progress=progress)

    extra_context = ""
    with center:
        extra_context = render_center(progress) or ""

    preview_payload = st.session_state.get("agent_column_preview")
    preview_codes: dict[str, str] = {}
    preview_lab = ""
    if isinstance(preview_payload, dict):
        raw_codes = preview_payload.get("challenge_codes")
        if isinstance(raw_codes, dict):
            preview_codes = {str(k): str(v) for k, v in raw_codes.items()}
        raw_lab = preview_payload.get("lab_code")
        if isinstance(raw_lab, str):
            preview_lab = raw_lab

    with right:
        render_agent_column(
            progress=progress,
            extra_context=extra_context,
            page_name=page_name,
            challenge_codes=preview_codes,
            lab_code=preview_lab,
        )

    st.markdown('<div id="dungeon-footer-anchor"></div>', unsafe_allow_html=True)
    render_footer_bar(progress)
    _paint_light_columns()
