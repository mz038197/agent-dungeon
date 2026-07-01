from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import streamlit as st

from agent_dungeon.core.progress import (
    LOOP_LEVEL_ID,
    DungeonProgress,
    challenge_complete,
    mark_forge_challenge_complete,
    save_user_progress,
    skill_forge_complete,
)
from agent_dungeon.forge.agent_py_store import write_loop_module_body
from agent_dungeon.forge.challenges import LOOP_FORGE_CHALLENGES, ForgeChallenge
from agent_dungeon.forge.forge_terminal_ui import render_agent_terminal
from agent_dungeon.forge.loop_validator import validate_loop_challenge
from agent_dungeon.forge.skill_forge_ui import (
    COLLAPSE_BUTTON_LABEL,
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

LOOP_FORGE_CONFIG_PREFIX = "loop_forge"

LOOP_FORGE_CONFIG = SkillForgeConfig(
    level_id=LOOP_LEVEL_ID,
    key_prefix=LOOP_FORGE_CONFIG_PREFIX,
    challenges=LOOP_FORGE_CHALLENGES,
    caption="跟著老師，替 Agent 裝上 Conversation Loop！",
    reward_ready="Loop 技能已就緒",
    reward_pending="完成四關 Skill Forge 後顯示獎勵",
)


def _sync_loop_to_agent_py(
    google_sub: str,
    code: str,
    *,
    progress: DungeonProgress,
) -> Path:
    path = write_loop_module_body(google_sub, code, progress=progress)
    return path


def _render_loop_challenge_card(
    *,
    challenge: ForgeChallenge,
    progress: DungeonProgress,
    google_sub: str | None,
    agent_py: Path,
    code: str,
    on_sync: Callable[[str, str], None],
) -> None:
    config = LOOP_FORGE_CONFIG
    done = challenge_complete(progress, challenge.id, level_id=LOOP_LEVEL_ID)
    editor_key = _editor_key(config, challenge.id)

    with st.container(border=True):
        st.markdown(f"**{challenge.label}** — {challenge.title}")
        render_editor_hint(f"💡 {challenge.editor_hint.strip() or challenge.title}")

        if editor_key not in st.session_state:
            st.session_state[editor_key] = code
        elif not done and not str(st.session_state.get(editor_key, "")).strip():
            st.session_state[editor_key] = code

        edited = st.text_area(
            "Loop 模組程式碼",
            height=200,
            key=editor_key,
            disabled=done,
            label_visibility="collapsed",
        )

        if google_sub is not None and not done:
            _sync_loop_to_agent_py(google_sub, edited, progress=progress)
            on_sync(challenge.id, edited)

        session_key = f"{LOOP_FORGE_CONFIG_PREFIX}_{challenge.id}_terminal"
        terminal_session = None
        if google_sub is not None and not done:
            terminal_session = render_agent_terminal(
                session_key=session_key,
                agent_py=agent_py,
                google_sub=google_sub,
                disabled=done,
            )

        if not done and st.button(
            "✅ 確認過關",
            key=f"{LOOP_FORGE_CONFIG_PREFIX}_{challenge.id}_confirm",
            type="primary",
            use_container_width=True,
        ):
            if google_sub is None:
                st.error("請先登入。")
            else:
                _sync_loop_to_agent_py(google_sub, edited, progress=progress)
                result = validate_loop_challenge(
                    challenge.id,
                    agent_py,
                    session=terminal_session,
                )
                if result.ok:
                    mark_forge_challenge_complete(progress, challenge.id, level_id=LOOP_LEVEL_ID)
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
            if challenge.id == "c2":
                hint = "請在終端機至少聊 2 輪（不含 bye），再按確認過關。"
            elif challenge.id == "c4":
                hint = "請在終端機至少完成 1 輪有效對話，再按確認過關。"
            else:
                hint = "確認程式碼結構正確後，按確認過關。"
            render_skill_forge_note(hint)


def render_loop_skill_forge(
    progress: DungeonProgress,
    *,
    google_sub: str | None,
    agent_py: Path,
    challenge_codes: dict[str, str],
    on_sync: Callable[[str, str], None],
) -> bool:
    config = LOOP_FORGE_CONFIG

    with st.container(border=True):
        st.markdown(
            '<span class="skill-forge-band" style="display:none"></span>',
            unsafe_allow_html=True,
        )
        render_skill_forge_summary(config.caption)

        forge_complete = skill_forge_complete(progress, level_id=LOOP_LEVEL_ID)
        done_count, total = _forge_progress(
            progress,
            level_id=LOOP_LEVEL_ID,
            challenges=LOOP_FORGE_CHALLENGES,
        )
        st.markdown(f"**進度：{done_count} / {total}**")

        for challenge in LOOP_FORGE_CHALLENGES:
            done = challenge_complete(progress, challenge.id, level_id=LOOP_LEVEL_ID)
            unlocked = _challenge_unlocked(
                progress,
                challenge,
                level_id=LOOP_LEVEL_ID,
                challenges=LOOP_FORGE_CHALLENGES,
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
                _render_loop_challenge_card(
                    challenge=challenge,
                    progress=progress,
                    google_sub=google_sub,
                    agent_py=agent_py,
                    code=challenge_codes.get(challenge.id, challenge.default_code),
                    on_sync=on_sync,
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
