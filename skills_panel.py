from __future__ import annotations

import html
from typing import Any

import streamlit as st

SkillItem = tuple[str, bool] | tuple[str, bool, str]

_BAR_STYLE = (
    "display:flex;align-items:center;justify-content:space-between;"
    "gap:1rem;flex-wrap:wrap;background:#f5f3ff;border:1px solid #ddd6fe;"
    "border-radius:12px;padding:0.75rem 1rem;margin-top:0.5rem;"
)
_COPY_STYLE = "display:flex;align-items:flex-start;gap:0.5rem;flex:1 1 220px;min-width:0;"
_BADGES_STYLE = (
    "display:flex;flex-wrap:wrap;gap:0.45rem;justify-content:flex-end;"
    "flex:1 1 280px;"
)
_BADGE_BASE = (
    "display:inline-flex;align-items:center;gap:0.35rem;"
    "border:1px solid #e2e8f0;border-radius:10px;padding:0.35rem 0.55rem;"
    "font-size:0.75rem;background:#ffffff;white-space:nowrap;"
)
_BADGE_UNLOCKED = _BADGE_BASE + "color:#0f172a;border-color:rgba(139,92,246,0.45);"
_BADGE_LOCKED = _BADGE_BASE + "color:#94a3b8;"


def _skill_parts(item: SkillItem) -> tuple[str, bool, str]:
    if len(item) == 3:
        label, unlocked, icon = item
        return str(label), bool(unlocked), str(icon)
    label, unlocked = item
    return str(label), bool(unlocked), "☑️"


def render_related_python_skills(
    skills: tuple[SkillItem, ...],
    *,
    subtitle: str = "想挑戰更多 Python 技能嗎？推薦你完成以下主題！",
    button_key: str | None = None,
    **legacy_kwargs: Any,
) -> None:
    _ = button_key
    _ = legacy_kwargs

    badges: list[str] = []
    for item in skills:
        label, unlocked, icon = _skill_parts(item)
        style = _BADGE_UNLOCKED if unlocked else _BADGE_LOCKED
        lock_html = (
            ""
            if unlocked
            else '<span style="font-size:0.72rem;margin-left:0.15rem;">🔒</span>'
        )
        badges.append(
            f'<div style="{style}">'
            f'<span>{html.escape(icon)}</span>'
            f"<span>{html.escape(label)}</span>"
            f"{lock_html}"
            f"</div>"
        )

    safe_subtitle = html.escape(subtitle)
    st.markdown(
        f"""
<div class="skills-panel-bar" style="{_BAR_STYLE}">
  <div style="{_COPY_STYLE}">
    <span style="font-size:1.25rem;line-height:1.2;">📖</span>
    <div>
      <div style="font-weight:800;font-size:0.92rem;color:#5b21b6;">
        RELATED PYTHON SKILLS (延伸學習)
      </div>
      <div style="font-size:0.78rem;color:#64748b;margin-top:0.1rem;line-height:1.35;">
        {safe_subtitle}
      </div>
    </div>
  </div>
  <div style="{_BADGES_STYLE}">
    {"".join(badges)}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
