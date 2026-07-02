from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import streamlit as st

from agent_dungeon.core.progress import (
    BRAIN_LEVEL_ID,
    DungeonProgress,
    challenge_complete,
    mark_forge_challenge_complete,
    save_user_progress,
    skill_forge_complete,
)
from agent_dungeon.forge.agent_py_store import write_agent_main_body
from agent_dungeon.forge.brain_validator import validate_brain_challenge
from agent_dungeon.forge.challenges import BRAIN_FORGE_CHALLENGES, ForgeChallenge
from agent_dungeon.forge.forge_terminal_ui import render_forge_inline_terminal
from agent_dungeon.forge.skill_forge_ui import (
    SkillForgeConfig,
    _challenge_unlocked,
    _editor_key,
    _forge_progress,
    _render_collapse_button,
    _render_completed_challenge,
    _render_locked_challenge,
    _render_reward_card,
    _set_awaiting_collapse,
    is_awaiting_collapse,
)
from agent_dungeon.ui.shell_ui import render_editor_hint, render_skill_forge_note, render_skill_forge_summary

BRAIN_FORGE_CONFIG_PREFIX = "brain_forge"

BRAIN_FORGE_CONFIG = SkillForgeConfig(
    level_id=BRAIN_LEVEL_ID,
    key_prefix=BRAIN_FORGE_CONFIG_PREFIX,
    challenges=BRAIN_FORGE_CHALLENGES,
    caption="跟著老師，一步步替 Agent 裝上 Brain！",
    reward_ready="Brain 技能已就緒",
    reward_pending="完成三關 Skill Forge 後顯示獎勵",
)
def _sync_brain_to_agent_py(
    google_sub: str,
    code: str,
    *,
    progress: DungeonProgress,
) -> Path:
    return write_agent_main_body(google_sub, code, progress=progress)


def _challenge_hint(challenge_id: str) -> str:
    if challenge_id == "c1":
        return "請在終端機輸入問題、確認 echo 後，再按確認過關。"
    if challenge_id == "c2":
        return "確認程式結構正確後，按確認過關（可選擇先在終端機試跑）。"
    if challenge_id == "c3":
        return "請在終端機執行並看到 Brain 回覆後，再按確認過關。"
    return "確認程式碼正確後，按確認過關。"


def _render_brain_challenge_card(
    *,
    challenge: ForgeChallenge,
    progress: DungeonProgress,
    google_sub: str | None,
    agent_py: Path,
    code: str,
    on_sync: Callable[[str, str], None],
    on_challenge_complete: Callable[[str, str], None] | None,
) -> None:
    config = BRAIN_FORGE_CONFIG
    done = challenge_complete(progress, challenge.id, level_id=BRAIN_LEVEL_ID)
    editor_key = _editor_key(config, challenge.id)

    with st.container(border=True):
        st.markdown(f"**{challenge.label}** — {challenge.title}")
        render_editor_hint(f"💡 {challenge.editor_hint.strip() or challenge.title}")

        if editor_key not in st.session_state:
            st.session_state[editor_key] = code
        elif not done and not str(st.session_state.get(editor_key, "")).strip():
            st.session_state[editor_key] = code

        edited = st.text_area(
            "Brain 模組程式碼",
            height=160,
            key=editor_key,
            disabled=done,
            label_visibility="collapsed",
        )

        render_skill_forge_note(
            "可選 model：`ollama_cloud@minimax-m3:cloud`、`openai@gpt-4o-mini`"
        )

        if google_sub is not None and not done:
            _sync_brain_to_agent_py(google_sub, edited, progress=progress)
            on_sync(challenge.id, edited)

        session_key = f"{BRAIN_FORGE_CONFIG_PREFIX}_{challenge.id}_terminal"
        terminal_session = None
        if google_sub is not None and not done:
            terminal_session = render_forge_inline_terminal(
                session_key=session_key,
                agent_py=agent_py,
                google_sub=google_sub,
                disabled=done,
            )

        if not done and st.button(
            "✅ 確認過關",
            key=f"{BRAIN_FORGE_CONFIG_PREFIX}_{challenge.id}_confirm",
            type="primary",
            use_container_width=True,
        ):
            if google_sub is None:
                st.error("請先登入。")
            else:
                _sync_brain_to_agent_py(google_sub, edited, progress=progress)
                result = validate_brain_challenge(
                    challenge.id,
                    agent_py,
                    session=terminal_session,
                )
                if result.ok:
                    if on_challenge_complete is not None:
                        on_challenge_complete(challenge.id, edited)
                    mark_forge_challenge_complete(progress, challenge.id, level_id=BRAIN_LEVEL_ID)
                    save_user_progress(google_sub, progress)
                    on_sync(challenge.id, edited)
                    _set_awaiting_collapse(config, challenge.id, awaiting=True)
                    st.rerun()
                else:
                    st.error(result.error or "尚未達成過關條件")

        if done:
            st.success("✅ 完成！")
            if is_awaiting_collapse(config, challenge.id):
                _render_collapse_button(config=config, challenge_id=challenge.id)
        else:
            render_skill_forge_note(_challenge_hint(challenge.id))


def render_brain_skill_forge(
    progress: DungeonProgress,
    *,
    google_sub: str | None,
    agent_py: Path,
    challenge_codes: dict[str, str],
    on_sync: Callable[[str, str], None],
    on_challenge_complete: Callable[[str, str], None] | None = None,
) -> bool:
    config = BRAIN_FORGE_CONFIG

    with st.container(border=True):
        st.markdown(
            '<span class="skill-forge-band" style="display:none"></span>',
            unsafe_allow_html=True,
        )
        render_skill_forge_summary(config.caption)

        forge_complete = skill_forge_complete(progress, level_id=BRAIN_LEVEL_ID)
        done_count, total = _forge_progress(
            progress,
            level_id=BRAIN_LEVEL_ID,
            challenges=BRAIN_FORGE_CHALLENGES,
        )
        st.markdown(f"**進度：{done_count} / {total}**")

        for challenge in BRAIN_FORGE_CHALLENGES:
            done = challenge_complete(progress, challenge.id, level_id=BRAIN_LEVEL_ID)
            unlocked = _challenge_unlocked(
                progress,
                challenge,
                level_id=BRAIN_LEVEL_ID,
                challenges=BRAIN_FORGE_CHALLENGES,
            )

            if done and is_awaiting_collapse(config, challenge.id):
                with st.container(border=True):
                    st.markdown(f"**{challenge.label}** — {challenge.title}")
                    st.code(
                        str(st.session_state.get(_editor_key(config, challenge.id), "")),
                        language="python",
                    )
                    st.success("✅ 完成！")
                    _render_collapse_button(config=config, challenge_id=challenge.id)
            elif done:
                _render_completed_challenge(
                    config=config,
                    challenge=challenge,
                    challenge_codes=challenge_codes,
                )
            elif not unlocked:
                _render_locked_challenge(challenge)
            else:
                _render_brain_challenge_card(
                    challenge=challenge,
                    progress=progress,
                    google_sub=google_sub,
                    agent_py=agent_py,
                    code=challenge_codes.get(challenge.id, challenge.default_code),
                    on_sync=on_sync,
                    on_challenge_complete=on_challenge_complete,
                )

        if forge_complete:
            _render_reward_card(
                complete=True,
                ready_text=config.reward_ready,
                pending_text=config.reward_pending,
            )
        else:
            render_skill_forge_note(config.reward_pending)

    return forge_complete
