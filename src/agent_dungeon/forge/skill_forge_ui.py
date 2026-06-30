from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import streamlit as st

from agent_dungeon.forge.challenges import BRAIN_FORGE_CHALLENGES, ForgeChallenge, VOICE_FORGE_CHALLENGES
from agent_dungeon.ui.shell_ui import (
    render_editor_hint,
    render_skill_forge_note,
    render_skill_forge_summary,
)
from agent_dungeon.forge.brain_runner import run_brain_forge_challenge
from agent_dungeon.forge.runner import ForgeRunResult, run_forge_challenge
from agent_dungeon.core.progress import (
    BRAIN_LEVEL_ID,
    DungeonProgress,
    VOICE_LEVEL_ID,
    challenge_complete,
    forge_challenge_ids_for_level,
    mark_forge_challenge_complete,
    save_user_progress,
    skill_forge_complete,
)


@dataclass(frozen=True)
class SkillForgeConfig:
    level_id: str
    key_prefix: str
    challenges: tuple[ForgeChallenge, ...]
    caption: str
    reward_ready: str
    reward_pending: str
    stdin_label: str = ""
    run_challenge: Callable[..., ForgeRunResult] | None = None


VOICE_FORGE_CONFIG = SkillForgeConfig(
    level_id=VOICE_LEVEL_ID,
    key_prefix="voice_forge",
    challenges=VOICE_FORGE_CHALLENGES,
    caption="跟著老師，一步步打造 Voice 技能！",
    reward_ready="Voice 技能已就緒",
    reward_pending="完成三關 Skill Forge 後顯示獎勵",
)

BRAIN_FORGE_CONFIG = SkillForgeConfig(
    level_id=BRAIN_LEVEL_ID,
    key_prefix="brain_forge",
    challenges=BRAIN_FORGE_CHALLENGES,
    caption="跟著老師，一步步替 Agent 裝上 Brain！",
    reward_ready="Brain 技能已就緒",
    reward_pending="完成三關 Skill Forge 後顯示獎勵",
    stdin_label="執行時 input() 會讀這裡的值",
    run_challenge=run_brain_forge_challenge,
)


def _challenge_unlocked(
    progress: DungeonProgress,
    challenge: ForgeChallenge,
    *,
    level_id: str,
    challenges: tuple[ForgeChallenge, ...],
) -> bool:
    if challenge.id == challenges[0].id:
        return True
    for index, item in enumerate(challenges):
        if item.id == challenge.id and index > 0:
            return challenge_complete(progress, challenges[index - 1].id, level_id=level_id)
    return False


def _forge_progress(
    progress: DungeonProgress,
    *,
    level_id: str,
    challenges: tuple[ForgeChallenge, ...],
) -> tuple[int, int]:
    done_count = sum(
        1 for challenge in challenges if challenge_complete(progress, challenge.id, level_id=level_id)
    )
    return done_count, len(challenges)


def _render_challenge_card(
    *,
    config: SkillForgeConfig,
    challenge: ForgeChallenge,
    progress: DungeonProgress,
    google_sub: str | None,
    code: str,
    stdout: str,
    stdin_value: str,
) -> None:
    done = challenge_complete(progress, challenge.id, level_id=config.level_id)

    with st.container(border=True):
        st.markdown(f"**{challenge.label}** — {challenge.title}")
        hint = challenge.editor_hint.strip() or challenge.title
        render_editor_hint(f"💡 {hint}")
        if config.level_id == BRAIN_LEVEL_ID and config.stdin_label:
            st.text_input(
                config.stdin_label,
                key=f"{config.key_prefix}_stdin",
                disabled=done,
            )
            stdin_value = str(st.session_state.get(f"{config.key_prefix}_stdin", stdin_value))

        editor_key = f"{config.key_prefix}_{challenge.id}_code"
        run_key = f"{config.key_prefix}_{challenge.id}_run"
        stdout_key = f"{config.key_prefix}_{challenge.id}_stdout"

        if editor_key not in st.session_state:
            st.session_state[editor_key] = code
        elif not done and not str(st.session_state.get(editor_key, "")).strip():
            st.session_state[editor_key] = code

        edited = st.text_area(
            "程式碼",
            height=160,
            key=editor_key,
            disabled=done,
            label_visibility="collapsed",
        )

        if config.level_id == BRAIN_LEVEL_ID:
            render_skill_forge_note(
                "可選 model：`ollama_cloud@minimax-m3:cloud`、`openai@gpt-4o-mini`"
            )

        if st.button(
            "▶ 執行",
            key=run_key,
            disabled=done,
            use_container_width=True,
            type="primary",
        ):
            if config.run_challenge is not None:
                result = config.run_challenge(
                    challenge.id,
                    edited,
                    google_sub=google_sub,
                    stdin_value=stdin_value,
                )
            else:
                result = run_forge_challenge(challenge.id, edited)
            st.session_state[stdout_key] = result.stdout
            if result.ok:
                if google_sub is not None:
                    mark_forge_challenge_complete(
                        progress,
                        challenge.id,
                        level_id=config.level_id,
                    )
                    save_user_progress(google_sub, progress)
                st.rerun()
            else:
                st.error(result.error or "執行失敗")

        display_stdout = st.session_state.get(stdout_key, stdout)
        if display_stdout.strip() or done:
            st.markdown("**▶ 執行結果**")
            st.code(display_stdout.strip() or "（無輸出）", language="text")

        if done:
            st.success("✅ 完成！")
        else:
            render_skill_forge_note("進行中…")


def _render_completed_challenge(
    *,
    challenge: ForgeChallenge,
    challenge_codes: dict[str, str],
) -> None:
    review_code = challenge_codes.get(challenge.id, challenge.default_code)
    st.markdown(f"✅ **{challenge.label}** — {challenge.title}")
    with st.expander("查看程式碼"):
        st.code(review_code, language="python")


def _render_locked_challenge(challenge: ForgeChallenge) -> None:
    st.markdown(f"🔒 **{challenge.label}** — {challenge.title}（先完成上一關）")


def _render_reward_card(*, complete: bool, ready_text: str, pending_text: str) -> None:
    with st.container(border=True):
        st.markdown("**鍛造完成**")
        if complete:
            st.markdown(
                f"""
<div style="text-align:center;font-size:2.2rem;padding:0.35rem 0;">🛡️⚒️✨</div>
<div style="text-align:center;font-weight:700;">鍛造完成！</div>
<div style="text-align:center;margin-bottom:0.5rem;">{ready_text}</div>
""",
                unsafe_allow_html=True,
            )
            st.success("可進入 Forge Lab")
        else:
            render_skill_forge_note(pending_text)


def render_skill_forge(
    progress: DungeonProgress,
    *,
    google_sub: str | None,
    challenge_codes: dict[str, str],
    challenge_stdout: dict[str, str],
    config: SkillForgeConfig = VOICE_FORGE_CONFIG,
    stdin_value: str = "",
) -> bool:
    challenges = config.challenges

    with st.container(border=True):
        st.markdown(
            '<span class="skill-forge-band" style="display:none"></span>',
            unsafe_allow_html=True,
        )
        render_skill_forge_summary(config.caption)

        forge_complete = skill_forge_complete(progress, level_id=config.level_id)
        done_count, total = _forge_progress(
            progress,
            level_id=config.level_id,
            challenges=challenges,
        )
        st.markdown(f"**進度：{done_count} / {total}**")

        for challenge in challenges:
            done = challenge_complete(progress, challenge.id, level_id=config.level_id)
            unlocked = _challenge_unlocked(
                progress,
                challenge,
                level_id=config.level_id,
                challenges=challenges,
            )

            if done:
                _render_completed_challenge(
                    challenge=challenge,
                    challenge_codes=challenge_codes,
                )
            elif not unlocked:
                _render_locked_challenge(challenge)
            else:
                _render_challenge_card(
                    config=config,
                    challenge=challenge,
                    progress=progress,
                    google_sub=google_sub,
                    code=challenge_codes.get(challenge.id, challenge.default_code),
                    stdout=challenge_stdout.get(challenge.id, ""),
                    stdin_value=stdin_value,
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
