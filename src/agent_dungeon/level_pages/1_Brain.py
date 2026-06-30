from __future__ import annotations

import importlib.util
from pathlib import Path


def _bootstrap_pkg_path() -> None:
    here = Path(__file__).resolve().parent
    bootstrap = (here.parent if here.name == "level_pages" else here) / "_bootstrap.py"
    spec = importlib.util.spec_from_file_location("_agent_dungeon_bootstrap", bootstrap)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"找不到 bootstrap：{bootstrap}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


_bootstrap_pkg_path()

import streamlit as st

from agent_dungeon.agent.agent_panel import append_assistant_message
from agent_dungeon.auth.session import get_auth_user
from agent_dungeon.core.dungeon_context import build_dungeon_extra_context
from agent_dungeon.core.page_bootstrap import init_dungeon_environment, require_dungeon_login
from agent_dungeon.core.progress import (
    BRAIN_LEVEL_ID,
    DungeonProgress,
    brain_module_online,
    challenge_complete,
    mark_brain_forge_lab_complete,
    quest_subtitle,
    save_user_progress,
    skill_forge_complete,
    voice_module_online,
)
from agent_dungeon.forge.brain_runner import run_brain_forge_lab_code
from agent_dungeon.forge.challenges import (
    BRAIN_FORGE_CHALLENGES,
    BRAIN_LEGACY_LAB_CODE,
    EMPTY_FORGE_LAB_CODE,
    brain_challenge_codes_from_stored,
    challenge_code_for_persist,
    forge_editor_code_needs_refresh,
    resolve_stored_lab_code,
)
from agent_dungeon.forge.skill_forge_ui import BRAIN_FORGE_CONFIG, render_skill_forge
from agent_dungeon.ui.dungeon_shell import dungeon_shell
from agent_dungeon.ui.mission_complete_ui import render_mission_complete_banner
from agent_dungeon.ui.section_heading_ui import render_level_heading, render_numbered_section_heading
from agent_dungeon.ui.shell_ui import (
    load_page_data,
    render_dungeon_hint,
    render_mission_demo,
    save_page_data,
)
from agent_dungeon.ui.skills_panel import render_related_python_skills

DEFAULT_LAB_PROMPT = "你是一位英文助教，用簡單英文回答。"

DEFAULT_LAB_CODE = EMPTY_FORGE_LAB_CODE

PAGE_NAME = "Brain"
STDOUT_KEY = "brain_forge_stdout"
LAB_CODE_KEY = "brain_forge_lab_code"
MISSION_CARD_HEIGHT = 300

BRAIN_RELATED_SKILLS = (
    ("f-string", True),
    ("strip()", False),
    ("replace()", False),
    ("len()", False),
    ("字串常用操作", False),
)

BRAIN_LEVEL_SUBTITLE = quest_subtitle(BRAIN_LEVEL_ID)

init_dungeon_environment()

st.set_page_config(
    page_title=f"第 2 關 · {BRAIN_LEVEL_SUBTITLE}",
    page_icon="🧠",
    layout="wide",
)

require_dungeon_login()


def _load_brain_page_data(google_sub: str | None) -> dict:
    if google_sub is None:
        return {}
    return load_page_data(PAGE_NAME)


def _challenge_codes_from_state(page_data: dict, progress: DungeonProgress) -> dict[str, str]:
    stored = page_data.get("challenges")
    completed = {
        challenge.id: challenge_complete(progress, challenge.id, level_id=BRAIN_LEVEL_ID)
        for challenge in BRAIN_FORGE_CHALLENGES
    }
    return brain_challenge_codes_from_stored(
        stored if isinstance(stored, dict) else None,
        completed=completed,
    )


def _sync_forge_code_session(challenge_codes: dict[str, str], progress: DungeonProgress) -> None:
    for index, challenge in enumerate(BRAIN_FORGE_CHALLENGES):
        key = f"brain_forge_{challenge.id}_code"
        expected = challenge_codes[challenge.id]
        done = challenge_complete(progress, challenge.id, level_id=BRAIN_LEVEL_ID)
        if st.session_state.get(key) is None:
            st.session_state[key] = expected
            continue
        if done:
            continue
        prev_complete = (
            index > 0
            and challenge_complete(
                progress,
                BRAIN_FORGE_CHALLENGES[index - 1].id,
                level_id=BRAIN_LEVEL_ID,
            )
        )
        current = str(st.session_state[key])
        unlock_empty = prev_complete and not current.strip()
        if unlock_empty or forge_editor_code_needs_refresh(
            challenge,
            current,
            expected=expected,
            completed=done,
            level="brain",
        ):
            st.session_state[key] = expected


def _sync_lab_code_session(lab_code: str, *, lab_done: bool, forge_done: bool) -> None:
    if not forge_done or lab_done:
        return
    if st.session_state.get(LAB_CODE_KEY) is None or not str(
        st.session_state.get(LAB_CODE_KEY, "")
    ).strip():
        st.session_state[LAB_CODE_KEY] = lab_code


def _challenge_stdout_from_state(page_data: dict) -> dict[str, str]:
    stdout_map: dict[str, str] = {}
    stored = page_data.get("stdout")
    if isinstance(stored, dict):
        for challenge in BRAIN_FORGE_CHALLENGES:
            raw = stored.get(challenge.id)
            if isinstance(raw, str):
                stdout_map[challenge.id] = raw
    return stdout_map


def _lab_code_from_state(page_data: dict, *, lab_done: bool) -> str:
    raw = page_data.get("code")
    return resolve_stored_lab_code(
        raw if isinstance(raw, str) else None,
        legacy=BRAIN_LEGACY_LAB_CODE,
        lab_done=lab_done,
    )


def _persist_brain_page_data(
    google_sub: str | None,
    page_data: dict,
    progress: DungeonProgress,
    *,
    lab_done: bool,
) -> None:
    if google_sub is None:
        return
    completed = {
        challenge.id: challenge_complete(progress, challenge.id, level_id=BRAIN_LEVEL_ID)
        for challenge in BRAIN_FORGE_CHALLENGES
    }
    stored = page_data.get("challenges")
    codes = brain_challenge_codes_from_stored(
        stored if isinstance(stored, dict) else None,
        completed=completed,
    )
    stdout_map: dict[str, str] = {}
    for challenge in BRAIN_FORGE_CHALLENGES:
        code_key = f"brain_forge_{challenge.id}_code"
        stdout_key = f"brain_forge_{challenge.id}_stdout"
        if code_key in st.session_state:
            codes[challenge.id] = challenge_code_for_persist(
                str(st.session_state[code_key]),
                default=codes[challenge.id],
                completed=completed[challenge.id],
            )
        if stdout_key in st.session_state:
            stdout_map[challenge.id] = str(st.session_state[stdout_key])
    page_data["challenges"] = codes
    page_data["stdout"] = stdout_map
    if STDOUT_KEY in st.session_state:
        page_data["lab_stdout"] = str(st.session_state[STDOUT_KEY])
    raw_lab = page_data.get("code")
    if isinstance(raw_lab, str) and not raw_lab.strip() and not lab_done:
        page_data["code"] = DEFAULT_LAB_CODE
    save_page_data(PAGE_NAME, page_data)


def render_level(progress: DungeonProgress) -> str:
    user = get_auth_user(st.session_state)
    google_sub = user.google_sub if user is not None else None

    if not voice_module_online(progress):
        render_level_heading(2, BRAIN_LEVEL_SUBTITLE)
        render_dungeon_hint("請先完成第 1 關 Voice，再來替 Agent 裝上 Brain！")
        return build_dungeon_extra_context(
            progress,
            page_name=PAGE_NAME,
            google_sub=google_sub,
            current_module="brain",
        )

    lab_done = brain_module_online(progress)
    forge_done = skill_forge_complete(progress, level_id=BRAIN_LEVEL_ID)

    page_data = _load_brain_page_data(google_sub)
    challenge_codes = _challenge_codes_from_state(page_data, progress)
    _sync_forge_code_session(challenge_codes, progress)
    challenge_stdout = _challenge_stdout_from_state(page_data)
    lab_code = _lab_code_from_state(page_data, lab_done=lab_done)
    _sync_lab_code_session(lab_code, lab_done=lab_done, forge_done=forge_done)

    preview_state = dict(st.session_state.get("agent_column_preview") or {})
    preview_state["brain_challenge_codes"] = challenge_codes
    preview_state["brain_lab_code"] = lab_code
    st.session_state["agent_column_preview"] = preview_state

    render_level_heading(2, BRAIN_LEVEL_SUBTITLE)

    render_numbered_section_heading(1, "MISSION", variant="purple")

    m1, m2, m3 = st.columns(3)
    with m1:
        with st.container(border=True, height=MISSION_CARD_HEIGHT):
            st.markdown("#### 📖 劇情")
            st.write(
                "Agent 已有 Voice，但沒有大腦，只能說固定台詞。"
                "完成 Forge，替它裝上 Brain！"
            )
    with m2:
        with st.container(border=True, height=MISSION_CARD_HEIGHT):
            st.markdown("#### 🎯 MISSION")
            st.write("讓 Agent 能根據不同問題，產生不同回答。")
            render_mission_demo(
                user_text="Python 是什麼？",
                agent_text="Python 是一種易讀、常用的程式語言，適合入門與自動化。",
            )
    with m3:
        with st.container(border=True, height=MISSION_CARD_HEIGHT):
            st.markdown("#### ✅ 完成條件")
            st.checkbox(
                "完成 Skill Forge 三關",
                value=forge_done,
                disabled=True,
            )
            st.checkbox(
                "Forge Lab：改過 prompt 且 Brain 成功回答",
                value=lab_done,
                disabled=True,
            )
            st.checkbox(
                "Agent 能根據不同問題產生不同回答",
                value=lab_done,
                disabled=True,
            )

    render_numbered_section_heading(2, "SKILL FORGE", variant="blue")
    render_skill_forge(
        progress,
        google_sub=google_sub,
        challenge_codes=challenge_codes,
        challenge_stdout=challenge_stdout,
        config=BRAIN_FORGE_CONFIG,
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
                height=260,
                key="brain_forge_lab_code_locked",
                disabled=True,
            )
        else:
            st.write(
                "修改 **prompt**，打造不同角色（例如：英文助教、數學老師、旅遊顧問），"
                "觀察 Brain 回答的差異。"
            )
            st.text_input(
                "執行時 input() 會讀這裡的值",
                key="brain_forge_lab_stdin",
            )
            code = st.text_area(
                "你的程式碼（自己完成）",
                value=lab_code,
                height=260,
                key=LAB_CODE_KEY,
                disabled=lab_done,
            )
            page_data["code"] = code if str(code).strip() else DEFAULT_LAB_CODE

            if st.button("執行", type="primary", disabled=lab_done, key="brain_forge_run_btn"):
                stdin_value = str(st.session_state.get("brain_forge_lab_stdin", ""))
                result = run_brain_forge_lab_code(
                    code,
                    google_sub=google_sub,
                    stdin_value=stdin_value,
                    default_prompt=DEFAULT_LAB_PROMPT,
                )
                if result.ok:
                    if google_sub is not None:
                        mark_brain_forge_lab_complete(progress)
                        save_user_progress(google_sub, progress)
                    reply = result.stdout.strip()
                    st.session_state[STDOUT_KEY] = reply
                    append_assistant_message(reply)
                    st.success("Forge Lab 通過！Brain 模組已上線。")
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
        with st.container(border=False):
            st.markdown(
                '<span class="dungeon-post-complete-band" style="display:none"></span>',
                unsafe_allow_html=True,
            )
            st.markdown("---")
            render_mission_complete_banner(
                message="太棒了！你的 Agent 真的會思考了！",
                next_level_label="Lv.3 Memory",
                next_level_icon="📗",
                next_page=None,
                button_key="brain_next_level_btn",
            )
            try:
                render_related_python_skills(
                    BRAIN_RELATED_SKILLS,
                    button_key="brain_skill_map_btn",
                )
            except Exception as exc:
                st.warning(f"延伸技能面板載入失敗：{exc}")

    _persist_brain_page_data(google_sub, page_data, progress, lab_done=lab_done)

    return build_dungeon_extra_context(
        progress,
        page_name=PAGE_NAME,
        google_sub=google_sub,
        current_module="brain",
    )


dungeon_shell(render_level, current_module="brain", page_name=PAGE_NAME)
