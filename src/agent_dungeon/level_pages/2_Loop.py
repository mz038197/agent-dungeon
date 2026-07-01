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

from agent_dungeon.auth.session import get_auth_user
from agent_dungeon.core.dungeon_context import build_dungeon_extra_context
from agent_dungeon.core.page_bootstrap import init_dungeon_environment, require_dungeon_login
from agent_dungeon.core.progress import (
    LOOP_LEVEL_ID,
    DungeonProgress,
    brain_module_online,
    challenge_complete,
    loop_module_online,
    mark_loop_forge_lab_complete,
    quest_subtitle,
    save_user_progress,
    skill_forge_complete,
)
from agent_dungeon.forge.agent_py_store import (
    agent_py_path,
    ensure_agent_py,
    migrate_page_data_to_agent_py,
    read_agent_main_body,
    read_module_for_editor,
    write_loop_module_body,
)
from agent_dungeon.forge.challenges import (
    EMPTY_FORGE_LAB_CODE,
    LOOP_FORGE_CHALLENGES,
    LOOP_LEGACY_LAB_CODE,
    challenge_code_for_persist,
    forge_editor_code_needs_refresh,
    loop_challenge_codes_from_stored,
    resolve_stored_lab_code,
)
from agent_dungeon.forge.forge_terminal_ui import render_agent_terminal
from agent_dungeon.forge.loop_skill_forge_ui import render_loop_skill_forge
from agent_dungeon.forge.loop_validator import validate_loop_forge_lab
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

DEFAULT_LAB_CODE = EMPTY_FORGE_LAB_CODE

PAGE_NAME = "Loop"
LAB_CODE_KEY = "loop_forge_lab_code"
MISSION_CARD_HEIGHT = 300

LOOP_RELATED_SKILLS = (
    ("pass", False),
    ("巢狀迴圈", False),
    ("for 與 while 比較", False),
)

LOOP_LEVEL_SUBTITLE = quest_subtitle(LOOP_LEVEL_ID)

init_dungeon_environment()

st.set_page_config(
    page_title=f"第 3 關 · {LOOP_LEVEL_SUBTITLE}",
    page_icon="🔁",
    layout="wide",
)

require_dungeon_login()


def _load_loop_page_data(google_sub: str | None) -> dict:
    if google_sub is None:
        return {}
    return load_page_data(PAGE_NAME)


def _brain_seed(google_sub: str, progress: DungeonProgress) -> str:
    migrate_page_data_to_agent_py(google_sub, progress=progress)
    return read_agent_main_body(google_sub, progress=progress)


def _challenge_codes_from_state(
    page_data: dict,
    progress: DungeonProgress,
    *,
    google_sub: str | None,
) -> dict[str, str]:
    stored = page_data.get("challenges")
    completed = {
        challenge.id: challenge_complete(progress, challenge.id, level_id=LOOP_LEVEL_ID)
        for challenge in LOOP_FORGE_CHALLENGES
    }
    brain_seed = _brain_seed(google_sub, progress) if google_sub else ""
    return loop_challenge_codes_from_stored(
        stored if isinstance(stored, dict) else None,
        completed=completed,
        brain_seed=brain_seed,
    )


def _persist_forge_challenge_code(
    google_sub: str | None,
    challenge_id: str,
    code: str,
) -> None:
    if google_sub is None:
        return
    page_data = _load_loop_page_data(google_sub)
    challenges = page_data.get("challenges")
    if not isinstance(challenges, dict):
        challenges = {}
    challenges[challenge_id] = code
    page_data["challenges"] = challenges
    save_page_data(PAGE_NAME, page_data)


def _on_loop_sync(challenge_id: str, code: str) -> None:
    user = get_auth_user(st.session_state)
    google_sub = user.google_sub if user is not None else None
    _persist_forge_challenge_code(google_sub, challenge_id, code)


def _sync_forge_code_session(
    challenge_codes: dict[str, str],
    progress: DungeonProgress,
) -> None:
    for index, challenge in enumerate(LOOP_FORGE_CHALLENGES):
        key = f"loop_forge_{challenge.id}_code"
        expected = challenge_codes[challenge.id]
        done = challenge_complete(progress, challenge.id, level_id=LOOP_LEVEL_ID)
        if st.session_state.get(key) is None:
            st.session_state[key] = expected
            continue
        if done:
            continue
        prev_complete = (
            index > 0
            and challenge_complete(
                progress,
                LOOP_FORGE_CHALLENGES[index - 1].id,
                level_id=LOOP_LEVEL_ID,
            )
        )
        current = str(st.session_state[key])
        unlock_empty = prev_complete and not current.strip()
        if unlock_empty or forge_editor_code_needs_refresh(
            challenge,
            current,
            expected=expected,
            completed=done,
            level="loop",
        ):
            st.session_state[key] = expected


def _lab_code_from_state(page_data: dict, *, lab_done: bool, google_sub: str | None, progress: DungeonProgress) -> str:
    if google_sub is not None:
        section = read_module_for_editor(
            google_sub,
            "loop",
            fallback="",
            progress=progress,
        )
        if section.strip() and lab_done:
            return section
    raw = page_data.get("code")
    return resolve_stored_lab_code(
        raw if isinstance(raw, str) else None,
        legacy=LOOP_LEGACY_LAB_CODE,
        lab_done=lab_done,
    )


def _persist_loop_page_data(
    google_sub: str | None,
    page_data: dict,
    progress: DungeonProgress,
    *,
    lab_done: bool,
) -> None:
    if google_sub is None:
        return
    completed = {
        challenge.id: challenge_complete(progress, challenge.id, level_id=LOOP_LEVEL_ID)
        for challenge in LOOP_FORGE_CHALLENGES
    }
    codes = loop_challenge_codes_from_stored(
        page_data.get("challenges") if isinstance(page_data.get("challenges"), dict) else None,
        completed=completed,
        brain_seed=_brain_seed(google_sub, progress),
    )
    for challenge in LOOP_FORGE_CHALLENGES:
        code_key = f"loop_forge_{challenge.id}_code"
        if code_key in st.session_state:
            codes[challenge.id] = challenge_code_for_persist(
                str(st.session_state[code_key]),
                default=codes[challenge.id],
                completed=completed[challenge.id],
            )
    page_data["challenges"] = codes
    raw_lab = page_data.get("code")
    if isinstance(raw_lab, str) and raw_lab.strip():
        write_loop_module_body(google_sub, raw_lab.strip(), progress=progress)
    save_page_data(PAGE_NAME, page_data)


def render_level(progress: DungeonProgress) -> str:
    user = get_auth_user(st.session_state)
    google_sub = user.google_sub if user is not None else None

    if not brain_module_online(progress):
        render_level_heading(3, LOOP_LEVEL_SUBTITLE)
        render_dungeon_hint("請先完成第 2 關 Brain，再來替 Agent 裝上 Loop！")
        return build_dungeon_extra_context(
            progress,
            page_name=PAGE_NAME,
            google_sub=google_sub,
            current_module="loop",
        )

    if google_sub is not None:
        migrate_page_data_to_agent_py(google_sub, progress=progress)
        ensure_agent_py(google_sub, progress=progress)

    lab_done = loop_module_online(progress)
    forge_done = skill_forge_complete(progress, level_id=LOOP_LEVEL_ID)

    page_data = _load_loop_page_data(google_sub)
    challenge_codes = _challenge_codes_from_state(page_data, progress, google_sub=google_sub)
    _sync_forge_code_session(challenge_codes, progress)
    lab_code = _lab_code_from_state(page_data, lab_done=lab_done, google_sub=google_sub, progress=progress)

    agent_file = agent_py_path(google_sub) if google_sub else None

    preview_state = dict(st.session_state.get("agent_column_preview") or {})
    if google_sub is not None:
        preview_state["agent_py_path"] = str(agent_file)
    st.session_state["agent_column_preview"] = preview_state

    render_level_heading(3, LOOP_LEVEL_SUBTITLE)

    render_numbered_section_heading(1, "MISSION", variant="purple")

    m1, m2, m3 = st.columns(3)
    with m1:
        with st.container(border=True, height=MISSION_CARD_HEIGHT):
            st.markdown("#### 📖 劇情")
            st.write(
                "Agent 擁有 Brain，但生命只有一瞬間，每回答一次就停止。"
                "完成 Forge，替它建立 Conversation Loop！"
            )
    with m2:
        with st.container(border=True, height=MISSION_CARD_HEIGHT):
            st.markdown("#### 🎯 MISSION")
            st.write("讓 Agent 能持續接收問題，直到使用者離開。")
            render_mission_demo(
                user_text="你好",
                agent_text="你好！有什麼我可以幫你的？",
            )
    with m3:
        with st.container(border=True, height=MISSION_CARD_HEIGHT):
            st.markdown("#### ✅ 完成條件")
            st.checkbox("完成 Skill Forge 四關", value=forge_done, disabled=True)
            st.checkbox("Forge Lab：help / clear / bye", value=lab_done, disabled=True)
            st.checkbox("終端機連續對話 ≥2 輪", value=lab_done, disabled=True)

    render_numbered_section_heading(2, "SKILL FORGE", variant="blue")
    if agent_file is not None and google_sub is not None:
        render_loop_skill_forge(
            progress,
            google_sub=google_sub,
            agent_py=agent_file,
            challenge_codes=challenge_codes,
            on_sync=_on_loop_sync,
        )
    else:
        render_dungeon_hint("請先登入以使用 Skill Forge。")

    render_numbered_section_heading(3, "🧪 FORGE LAB", variant="green")
    with st.container(border=True):
        st.markdown(
            '<span class="dungeon-forge-lab-band" style="display:none"></span>',
            unsafe_allow_html=True,
        )

        if not forge_done:
            render_dungeon_hint("先完成上方 Skill Forge 四關，再來 Forge Lab！")
            st.text_area(
                "Loop 模組（自己完成）",
                value=lab_code,
                height=260,
                key="loop_forge_lab_code_locked",
                disabled=True,
            )
        else:
            st.write("在 **Loop 模組** 加入 `help`、`clear`、`bye`；用下方終端機試聊。")
            code = st.text_area(
                "Loop 模組（自己完成）",
                value=lab_code,
                height=260,
                key=LAB_CODE_KEY,
                disabled=lab_done,
            )
            page_data["code"] = code if str(code).strip() else DEFAULT_LAB_CODE

            if google_sub is not None and str(code).strip():
                write_loop_module_body(google_sub, str(code).strip(), progress=progress)

            terminal_session = None
            if google_sub is not None and agent_file is not None:
                terminal_session = render_agent_terminal(
                    session_key="loop_forge_lab_terminal",
                    agent_py=agent_file,
                    google_sub=google_sub,
                    disabled=lab_done,
                )

            if st.button(
                "完成 Forge Lab",
                type="primary",
                disabled=lab_done,
                key="loop_forge_lab_complete_btn",
            ):
                if google_sub is None or agent_file is None:
                    st.error("請先登入。")
                else:
                    write_loop_module_body(google_sub, str(code).strip(), progress=progress)
                    result = validate_loop_forge_lab(agent_file, session=terminal_session)
                    if result.ok:
                        mark_loop_forge_lab_complete(progress)
                        save_user_progress(google_sub, progress)
                        st.success("Forge Lab 通過！Loop 模組已上線。")
                        st.rerun()
                    else:
                        st.error(result.error or "尚未達成 Forge Lab 條件")

    if lab_done:
        with st.container(border=False):
            st.markdown(
                '<span class="dungeon-post-complete-band" style="display:none"></span>',
                unsafe_allow_html=True,
            )
            st.markdown("---")
            render_mission_complete_banner(
                message="太棒了！你的 Agent 可以一直陪你聊了！",
                next_level_label="Lv.4 Identity",
                next_level_icon="🤖",
                next_page=None,
                button_key="loop_next_level_btn",
            )
            try:
                render_related_python_skills(
                    LOOP_RELATED_SKILLS,
                    button_key="loop_skill_map_btn",
                )
            except Exception as exc:
                st.warning(f"延伸技能面板載入失敗：{exc}")

    _persist_loop_page_data(google_sub, page_data, progress, lab_done=lab_done)

    return build_dungeon_extra_context(
        progress,
        page_name=PAGE_NAME,
        google_sub=google_sub,
        current_module="loop",
    )


dungeon_shell(render_level, current_module="loop", page_name=PAGE_NAME)
