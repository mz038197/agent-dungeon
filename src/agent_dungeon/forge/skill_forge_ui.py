from __future__ import annotations

import streamlit as st

from agent_dungeon.forge.challenges import VOICE_FORGE_CHALLENGES, ForgeChallenge
from agent_dungeon.forge.runner import run_forge_challenge
from agent_dungeon.core.progress import (
    DungeonProgress,
    challenge_complete,
    mark_forge_challenge_complete,
    save_user_progress,
    skill_forge_complete,
)


def _challenge_unlocked(progress: DungeonProgress, challenge: ForgeChallenge) -> bool:
    if challenge.id == "c1":
        return True
    if challenge.id == "c2":
        return challenge_complete(progress, "c1")
    if challenge.id == "c3":
        return challenge_complete(progress, "c2")
    return False


def _forge_progress(progress: DungeonProgress) -> tuple[int, int]:
    challenges = VOICE_FORGE_CHALLENGES
    done_count = sum(1 for challenge in challenges if challenge_complete(progress, challenge.id))
    return done_count, len(challenges)


def _render_challenge_card(
    *,
    challenge: ForgeChallenge,
    progress: DungeonProgress,
    google_sub: str | None,
    code: str,
    stdout: str,
) -> None:
    done = challenge_complete(progress, challenge.id)

    with st.container(border=True):
        st.markdown(f"**{challenge.label}** — {challenge.title}")

        editor_key = f"voice_forge_{challenge.id}_code"
        run_key = f"voice_forge_{challenge.id}_run"
        stdout_key = f"voice_forge_{challenge.id}_stdout"

        if editor_key not in st.session_state:
            st.session_state[editor_key] = code

        edited = st.text_area(
            "程式碼",
            height=160,
            key=editor_key,
            disabled=done,
            label_visibility="collapsed",
        )

        if st.button(
            "▶ 執行",
            key=run_key,
            disabled=done,
            use_container_width=True,
            type="primary",
        ):
            result = run_forge_challenge(challenge.id, edited)
            st.session_state[stdout_key] = result.stdout
            if result.ok:
                if google_sub is not None:
                    mark_forge_challenge_complete(progress, challenge.id)
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
            st.caption("進行中…")


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


def _render_reward_card(*, complete: bool) -> None:
    with st.container(border=True):
        st.markdown("**鍛造完成**")
        if complete:
            st.markdown(
                """
<div style="text-align:center;font-size:2.2rem;padding:0.35rem 0;">🛡️⚒️✨</div>
<div style="text-align:center;font-weight:700;">鍛造完成！</div>
<div style="text-align:center;margin-bottom:0.5rem;">Voice 技能已就緒</div>
""",
                unsafe_allow_html=True,
            )
            st.success("可進入 Forge Lab")
        else:
            st.caption("完成三關 Skill Forge 後顯示獎勵")


def render_skill_forge(
    progress: DungeonProgress,
    *,
    google_sub: str | None,
    challenge_codes: dict[str, str],
    challenge_stdout: dict[str, str],
) -> bool:
    with st.container(border=True):
        st.markdown(
            '<span class="skill-forge-band" style="display:none"></span>',
            unsafe_allow_html=True,
        )
        st.caption("跟著老師，一步步打造 Voice 技能！")

        forge_complete = skill_forge_complete(progress)
        challenges = VOICE_FORGE_CHALLENGES
        done_count, total = _forge_progress(progress)
        st.markdown(f"**進度：{done_count} / {total}**")

        for challenge in challenges:
            done = challenge_complete(progress, challenge.id)
            unlocked = _challenge_unlocked(progress, challenge)

            if done:
                _render_completed_challenge(
                    challenge=challenge,
                    challenge_codes=challenge_codes,
                )
            elif not unlocked:
                _render_locked_challenge(challenge)
            else:
                _render_challenge_card(
                    challenge=challenge,
                    progress=progress,
                    google_sub=google_sub,
                    code=challenge_codes.get(challenge.id, challenge.default_code),
                    stdout=challenge_stdout.get(challenge.id, ""),
                )

        if forge_complete:
            _render_reward_card(complete=True)
        else:
            st.caption("完成三關 Skill Forge 後顯示獎勵")

    return forge_complete
