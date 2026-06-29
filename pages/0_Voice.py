from __future__ import annotations

import streamlit as st

from agent_panel import append_assistant_message
from auth.session import get_auth_user
from dungeon_context import build_dungeon_extra_context
from dungeon_shell import dungeon_shell
from forge_challenges import (
    LEGACY_ANSWER_CODES,
    VOICE_FORGE_CHALLENGES,
    challenge_codes_from_stored,
)
from forge_runner import run_forge_lab_code
from mission_complete_ui import render_mission_complete_banner
from page_bootstrap import init_dungeon_environment, require_dungeon_login
from progress import (
    DungeonProgress,
    challenge_complete,
    mark_forge_lab_complete,
    quest_subtitle,
    quest_tag,
    save_user_progress,
    skill_forge_complete,
    voice_module_online,
)
from section_heading_ui import render_level_heading, render_numbered_section_heading
from shell_ui import (
    load_page_data,
    render_dungeon_hint,
    render_mission_demo,
    save_page_data,
)
from skill_forge_ui import render_skill_forge
from skills_panel import render_related_python_skills

DEFAULT_LAB_CODE = """def speak():
    print("Hello, I am your AI assistant!")
    print("Nice to meet you!")

speak()
"""

PAGE_NAME = "Voice"
STDOUT_KEY = "voice_forge_stdout"
MISSION_CARD_HEIGHT = 300

VOICE_RELATED_SKILLS = (
    ("print()", True),
    ("input()", False),
    ("escape", False),
    ("多行字串", False),
    ("sep", False),
    ("end", False),
)


VOICE_LEVEL_ID = "1"
VOICE_LEVEL_SUBTITLE = quest_subtitle(VOICE_LEVEL_ID)

init_dungeon_environment()

st.set_page_config(
    page_title=f"第 1 關 · {VOICE_LEVEL_SUBTITLE}",
    page_icon="🎙️",
    layout="wide",
)

require_dungeon_login()


def _default_challenge_codes() -> dict[str, str]:
    return {challenge.id: challenge.default_code for challenge in VOICE_FORGE_CHALLENGES}


def _load_voice_page_data(google_sub: str | None) -> dict:
    if google_sub is None:
        return {}
    return load_page_data(PAGE_NAME)


def _challenge_codes_from_state(page_data: dict, progress: DungeonProgress) -> dict[str, str]:
    stored = page_data.get("challenges")
    completed = {
        challenge.id: challenge_complete(progress, challenge.id)
        for challenge in VOICE_FORGE_CHALLENGES
    }
    return challenge_codes_from_stored(
        stored if isinstance(stored, dict) else None,
        completed=completed,
    )


def _sync_forge_code_session(challenge_codes: dict[str, str]) -> None:
    for challenge in VOICE_FORGE_CHALLENGES:
        key = f"voice_forge_{challenge.id}_code"
        expected = challenge_codes[challenge.id]
        current = st.session_state.get(key)
        if current is None:
            st.session_state[key] = expected
        elif current == LEGACY_ANSWER_CODES.get(challenge.id):
            st.session_state[key] = expected


def _challenge_stdout_from_state(page_data: dict) -> dict[str, str]:
    stdout_map: dict[str, str] = {}
    stored = page_data.get("stdout")
    if isinstance(stored, dict):
        for challenge in VOICE_FORGE_CHALLENGES:
            raw = stored.get(challenge.id)
            if isinstance(raw, str):
                stdout_map[challenge.id] = raw
    return stdout_map


def _lab_code_from_state(page_data: dict) -> str:
    raw = page_data.get("code")
    if isinstance(raw, str) and raw.strip():
        return raw
    return DEFAULT_LAB_CODE


def _persist_voice_page_data(google_sub: str | None, page_data: dict) -> None:
    if google_sub is None:
        return
    codes = _default_challenge_codes()
    stdout_map: dict[str, str] = {}
    for challenge in VOICE_FORGE_CHALLENGES:
        code_key = f"voice_forge_{challenge.id}_code"
        stdout_key = f"voice_forge_{challenge.id}_stdout"
        if code_key in st.session_state:
            codes[challenge.id] = str(st.session_state[code_key])
        if stdout_key in st.session_state:
            stdout_map[challenge.id] = str(st.session_state[stdout_key])
    page_data["challenges"] = codes
    page_data["stdout"] = stdout_map
    if STDOUT_KEY in st.session_state:
        page_data["lab_stdout"] = str(st.session_state[STDOUT_KEY])
    save_page_data(PAGE_NAME, page_data)


def render_level(progress: DungeonProgress) -> str:
    user = get_auth_user(st.session_state)
    google_sub = user.google_sub if user is not None else None
    lab_done = voice_module_online(progress)
    forge_done = skill_forge_complete(progress)

    page_data = _load_voice_page_data(google_sub)
    challenge_codes = _challenge_codes_from_state(page_data, progress)
    _sync_forge_code_session(challenge_codes)
    challenge_stdout = _challenge_stdout_from_state(page_data)
    lab_code = _lab_code_from_state(page_data)
    st.session_state["agent_column_preview"] = {
        "challenge_codes": challenge_codes,
        "lab_code": lab_code,
    }

    render_level_heading(1, VOICE_LEVEL_SUBTITLE, tag=quest_tag(VOICE_LEVEL_ID))

    render_numbered_section_heading(1, "MISSION", variant="purple")

    m1, m2, m3 = st.columns(3)
    with m1:
        with st.container(border=True, height=MISSION_CARD_HEIGHT):
            st.markdown("#### 📖 劇情")
            st.write(
                "Agent 剛被創造出來，但還沒有 voice 模組，無法開口回應。"
                "完成 Forge，替它裝上第一個聲音！"
            )
    with m2:
        with st.container(border=True, height=MISSION_CARD_HEIGHT):
            st.markdown("#### 🎯 MISSION")
            st.write("讓你的 Agent 說出第一句話。")
            render_mission_demo(
                user_text="Hello",
                agent_text="Hello, I am your AI assistant!",
            )
    with m3:
        with st.container(border=True, height=MISSION_CARD_HEIGHT):
            st.markdown("#### ✅ 完成條件")
            st.checkbox("完成 Skill Forge 三關", value=forge_done, disabled=True)
            st.checkbox("Agent 成功輸出至少兩句話", value=lab_done, disabled=True)
            st.checkbox("定義並呼叫 speak()", value=lab_done, disabled=True)

    render_numbered_section_heading(2, "SKILL FORGE", variant="blue")
    render_skill_forge(
        progress,
        google_sub=google_sub,
        challenge_codes=challenge_codes,
        challenge_stdout=challenge_stdout,
    )

    render_numbered_section_heading(3, "🧪 FORGE LAB", variant="green")
    with st.container(border=True):
        st.markdown(
            '<span class="dungeon-forge-lab-band" style="display:none"></span>',
            unsafe_allow_html=True,
        )

        if not forge_done:
            render_dungeon_hint("先完成上方 Skill Forge 三關，再來 Forge Lab！")
            st.text_area(
                "你的程式碼（自己完成）",
                value=lab_code,
                height=220,
                key="voice_forge_lab_code_locked",
                disabled=True,
            )
        else:
            st.write("修改 Agent 自我介紹，至少輸出 **兩句話**，並建立自己的開場白。")
            code = st.text_area(
                "你的程式碼（自己完成）",
                value=lab_code,
                height=220,
                key="voice_forge_lab_code",
                disabled=lab_done,
            )
            page_data["code"] = code

            if st.button("執行", type="primary", disabled=lab_done, key="forge_run_btn"):
                result = run_forge_lab_code(code)
                if result.ok:
                    if google_sub is not None:
                        mark_forge_lab_complete(progress)
                        save_user_progress(google_sub, progress)
                    st.session_state[STDOUT_KEY] = result.stdout.strip()
                    append_assistant_message(result.stdout.strip())
                    st.success("Forge Lab 通過！Voice 模組已上線。")
                    st.rerun()
                else:
                    st.error(result.error or "執行失敗")
                    if result.stdout.strip():
                        st.code(result.stdout, language="text")

            preview = st.session_state.get(STDOUT_KEY, page_data.get("lab_stdout", ""))
            if lab_done and preview:
                st.markdown("**執行結果預覽**")
                st.code(str(preview), language="text")

    if lab_done:
        st.markdown("---")
        render_mission_complete_banner(
            message="太棒了！你的 Agent 可以持續陪伴你，隨時等待任務！",
            next_level_label="Lv.2 Brain",
            next_level_icon="🧠",
            next_page=None,
            button_key="voice_next_level_btn",
        )
        try:
            render_related_python_skills(
                VOICE_RELATED_SKILLS,
                button_key="voice_skill_map_btn",
            )
        except Exception as exc:
            st.warning(f"延伸技能面板載入失敗：{exc}")

    _persist_voice_page_data(google_sub, page_data)

    return build_dungeon_extra_context(
        progress,
        page_name=PAGE_NAME,
        google_sub=google_sub,
        current_module="voice",
    )


dungeon_shell(render_level, current_module="voice", page_name=PAGE_NAME)
