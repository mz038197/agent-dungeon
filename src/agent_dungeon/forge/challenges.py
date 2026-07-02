from __future__ import annotations

import ast
from dataclasses import dataclass

from agent_dungeon.forge.code_checks import (
    has_brain_constructor,
    has_input_call,
    has_main_call_in_main_guard,
)
from agent_dungeon.forge.llm_provider import DEFAULT_BRAIN_MODEL

CHALLENGE_IDS = ("c1", "c2", "c3")

VOICE_FORGE_CHALLENGE_IDS = CHALLENGE_IDS
BRAIN_FORGE_CHALLENGE_IDS = CHALLENGE_IDS
LOOP_FORGE_CHALLENGE_IDS = ("c1", "c2", "c3", "c4")

_BRAIN_C1_LEGACY_STARTER = """# 讀取使用者輸入
question = input("你想問什麼？ ")
print(question)
""".strip()

_BRAIN_C1_HINT = """    # TODO: 用 input() 取得 question，再用 print 顯示
    # Code Here #"""

_EMPTY_MAIN = "def main():\n    pass"


@dataclass(frozen=True)
class ForgeChallenge:
    id: str
    label: str
    title: str
    default_code: str
    editor_hint: str = ""


_VOICE_C2_HINT = """# --- 本關：建立 main() ---
# 提示：用 def 定義函式，把上一關的 print 放進去
# Code Here #"""

_VOICE_C2_LEGACY_HINT = _VOICE_C2_HINT

_VOICE_C2_LEGACY_SKELETON_HINT = """# --- 本關：建立 main() ---
# def main():
#     print("Hello")
# Code Here #"""

_VOICE_C2_LEGACY_HINT_OLD = _VOICE_C2_LEGACY_SKELETON_HINT

_VOICE_C2_LEGACY_AUTO_WRAP = """def main():
    # TODO: 用 print 輸出 Hello
    # Code Here #
    pass"""

_VOICE_C3_SUFFIX = """if __name__ == "__main__":
    # --- 本關：在這裡呼叫 main()，讓 Agent 說話 ---
    # Code Here #"""

_VOICE_C3_LEGACY_IF_NAME = """if __name__ == "__main__":
    # --- 本關：在這裡呼叫 main()，讓 Agent 說話 ---
    # main()
    # （記得把 main 內的輸出改成 Hello!）
    # Code Here #"""

_VOICE_C3_LEGACY_IF_NAME_V2 = """if __name__ == "__main__":
    # --- 本關：啟動 main() ---
    # 提示：呼叫 main()，並把 main 內輸出改成 Hello!"""

_VOICE_C3_LEGACY_MAIN_BODY_HINT = """    # TODO: 輸出 Hello!（記得驚嘆號）
    # Code Here #"""

_VOICE_LAB_HINT = """    # --- 本關：再加一句自我介紹 ---
    # Code Here #"""

VOICE_FORGE_CHALLENGES: tuple[ForgeChallenge, ...] = (
    ForgeChallenge(
        id="c1",
        label="Challenge 1",
        title="認識 print()",
        default_code='# 使用 print 函式 輸出 "Hello" !',
        editor_hint='使用 print 函式輸出 "Hello" !',
    ),
    ForgeChallenge(
        id="c2",
        label="Challenge 2",
        title="建立 main()",
        default_code=_VOICE_C2_HINT,
        editor_hint="自己寫 def main():，把上一關的 print 放進函式裡",
    ),
    ForgeChallenge(
        id="c3",
        label="Final Challenge",
        title="讓 Agent 說話！",
        default_code=_VOICE_C3_SUFFIX,
        editor_hint='在 if __name__ == "__main__": 區塊內自己寫 main() 啟動程式',
    ),
)

_BRAIN_C2_SUFFIX = """    # --- 本關：建立 Brain（llm 放在 question 之前）---"""

_BRAIN_C2_LEGACY_ANSWER = f"""    # --- 本關：建立 Brain（llm 放在 question 之前）---
    llm = Brain(model="{DEFAULT_BRAIN_MODEL}")"""

_BRAIN_C3_SUFFIX = """    # --- 本關：完成 Brain 安裝 ---"""

BRAIN_FORGE_CHALLENGES: tuple[ForgeChallenge, ...] = (
    ForgeChallenge(
        id="c1",
        label="Challenge 1",
        title="讀取使用者輸入",
        default_code=f"""def main():
{_BRAIN_C1_HINT}
    pass""",
        editor_hint="在 main() 內用 input() 讀取問題，再用 print 顯示讀到的內容",
    ),
    ForgeChallenge(
        id="c2",
        label="Challenge 2",
        title="建立 Brain",
        default_code=_BRAIN_C2_SUFFIX,
        editor_hint='在 question 之前建立 Brain（llm = Brain(model="...")）',
    ),
    ForgeChallenge(
        id="c3",
        label="Final Challenge",
        title="完成 Brain 安裝",
        default_code=_BRAIN_C3_SUFFIX,
        editor_hint="整合上方步驟：invoke(question) 後 print Brain 的回覆",
    ),
)

BRAIN_LEGACY_ANSWER_CODES: dict[str, str] = {}

EMPTY_FORGE_LAB_CODE = ""

VOICE_LEGACY_LAB_CODE = """def main():
    print("Hello, I am your AI assistant!")
    print("Nice to meet you!")
""".strip()

_BRAIN_LEGACY_LAB_PROMPT = "你是一位英文助教，用簡單英文回答。"

BRAIN_LEGACY_LAB_CODE = f"""def main():
    prompt = "{_BRAIN_LEGACY_LAB_PROMPT}"
    llm = Brain(model="{DEFAULT_BRAIN_MODEL}")
    question = input("你想問什麼？ ")
    response = llm.invoke(f"{{prompt}}\\n\\n問題：{{question}}")
    print(response)
""".strip()

_LOOP_C1_HINT = """    # --- 本關：用 while True 包住下方 input 起的對話邏輯 ---
    # Code Here #"""

_LOOP_C1_HINT_MARKER = "while True 包住"

_LOOP_C2_HINT = """        # --- 本關：bye 離開 ---
        # if question == "bye":
        #     print("bye bye!")
        #     break
        # Code Here #"""

_LOOP_C3_HINT = """        # --- 本關：空字串跳過 ---
        # if not question.strip():
        #     continue
        # Code Here #"""

_LOOP_C4_HINT = """        # --- 本關：invoke + print ---
        # response = llm.invoke(...)
        # print(response)
        # Code Here #"""

LOOP_FORGE_CHALLENGES: tuple[ForgeChallenge, ...] = (
    ForgeChallenge(
        id="c1",
        label="Challenge 1",
        title="建立對話迴圈",
        default_code=_LOOP_C1_HINT.strip(),
        editor_hint="用 while True 包住 input 起的對話；加上 bye → break",
    ),
    ForgeChallenge(
        id="c2",
        label="Challenge 2",
        title="bye 離開",
        default_code=_LOOP_C2_HINT.strip(),
        editor_hint='bye 時 print("bye bye!") 再 break；終端機至少聊 2 輪',
    ),
    ForgeChallenge(
        id="c3",
        label="Challenge 3",
        title="空字串 continue",
        default_code=_LOOP_C3_HINT.strip(),
        editor_hint="空 Enter 用 continue 跳過，不當成新問題",
    ),
    ForgeChallenge(
        id="c4",
        label="Final Challenge",
        title="連續問答",
        default_code=_LOOP_C4_HINT.strip(),
        editor_hint="在迴圈內完成 invoke + print；終端機至少聊 1 輪",
    ),
)

LOOP_LEGACY_LAB_CODE = f"""def main():
    prompt = "你是一位友善助教。"
    llm = Brain(model="{DEFAULT_BRAIN_MODEL}")
    while True:
        question = input("> ")
        if question == "bye":
            print("bye bye!")
            break
        if not question.strip():
            continue
        if question == "help":
            print("指令：help / clear / bye")
            continue
        if question == "clear":
            print("（對話已清除）")
            continue
        response = llm.invoke(f"{{prompt}}\\n\\n問題：{{question}}")
        print(response)
""".strip()

# 舊版預設含答案；未完成關卡若仍存這些內容，改回現行註解提示。
LEGACY_ANSWER_CODES: dict[str, str] = {
    "c1": 'print("Hello")',
    "c2": 'def main():\n    print("Hello")',
    "c3": 'def main():\n    print("Hello!")',
}

VOICE_LEGACY_TEMPLATE_CODES: dict[str, str] = {
    "c2": "# 定義 speak() 函式，在函式內輸出 Hello",
    "c3": "# 定義 speak() 函式，並呼叫 speak() 輸出 Hello!（記得驚嘆號）",
}

VOICE_LEGACY_SPEAK_ANSWER_CODES: dict[str, str] = {
    "c2": 'def speak():\n    print("Hello")',
    "c3": 'def speak():\n    print("Hello!")\n\nspeak()',
}


def _voice_legacy_stored_values(challenge_id: str) -> set[str]:
    values: set[str] = set()
    for mapping in (LEGACY_ANSWER_CODES, VOICE_LEGACY_TEMPLATE_CODES, VOICE_LEGACY_SPEAK_ANSWER_CODES):
        raw = mapping.get(challenge_id)
        if isinstance(raw, str) and raw.strip():
            values.add(raw.strip())
    if challenge_id == "c2":
        values.add(_VOICE_C2_LEGACY_HINT.strip())
        values.add(_VOICE_C2_LEGACY_SKELETON_HINT.strip())
        values.add(_VOICE_C2_LEGACY_HINT_OLD.strip())
        values.add(_VOICE_C2_LEGACY_AUTO_WRAP.strip())
    if challenge_id == "c3":
        values.add(_VOICE_C3_LEGACY_IF_NAME.strip())
        values.add(_VOICE_C3_LEGACY_IF_NAME_V2.strip())
        values.add(_VOICE_C3_LEGACY_MAIN_BODY_HINT.strip())
    return values


def _voice_c2_template_with_prior(prior_code: str) -> str:
    hint = _VOICE_C2_HINT.strip()
    prior = prior_code.strip()
    if not prior:
        return hint
    return f"{hint}\n{prior}"


def _voice_c2_stored_is_stale(stored: str, *, default: str) -> bool:
    stripped = stored.strip()
    if stripped == default.strip():
        return False
    if "# def main():" in stripped:
        return True
    if "# TODO: 用 print 輸出 Hello" in stripped:
        return True
    if any(line.strip() == '# print("Hello")' for line in stripped.splitlines()):
        return True
    hello_at = stripped.find('print("Hello")')
    hint_at = stripped.find("本關")
    if hello_at >= 0 and hint_at >= 0 and hello_at < hint_at:
        return True
    return False


def _voice_c3_stored_is_stale(stored: str, *, default: str) -> bool:
    stripped = stored.strip()
    if stripped == default.strip():
        return False
    if "if __name__" not in stripped:
        return False
    if "# main()" in stripped:
        return True
    if "Hello!" in stripped:
        return True
    return False


def _voice_stored_needs_carry_forward(
    challenge: ForgeChallenge,
    stored: str,
    *,
    default: str,
    completed: bool,
) -> bool:
    if completed:
        return False
    stripped = stored.strip()
    if not stripped:
        return True
    if stripped == default.strip():
        return False
    if stripped == challenge.default_code.strip():
        return True
    if not completed and stripped in _voice_legacy_stored_values(challenge.id):
        return True
    if challenge.id == "c2":
        if stripped in {
            _VOICE_C2_LEGACY_HINT.strip(),
            _VOICE_C2_LEGACY_SKELETON_HINT.strip(),
            _VOICE_C2_LEGACY_HINT_OLD.strip(),
            _VOICE_C2_LEGACY_AUTO_WRAP.strip(),
        }:
            return True
        if "# TODO: 用 print 輸出 Hello" in stripped and _voice_has_executable_main(stripped):
            return True
        if _voice_c2_stored_is_stale(stripped, default=default):
            return True
        if default.strip() != challenge.default_code.strip() and not _voice_has_executable_main(stripped):
            if "本關" in stripped and "print(" not in stripped:
                return True
        return False
    if challenge.id == "c3":
        if stripped in {
            _VOICE_C3_LEGACY_IF_NAME.strip(),
            _VOICE_C3_LEGACY_IF_NAME_V2.strip(),
            _VOICE_C3_LEGACY_MAIN_BODY_HINT.strip(),
        }:
            return True
        if _voice_c3_stored_is_stale(stripped, default=default):
            return True
        if default.strip().startswith(stripped.rstrip()) and stripped != default.strip():
            return True
        if "if __name__" in stripped and not _voice_has_executable_main(stripped):
            return True
        if _voice_has_executable_main(stripped) and "if __name__" not in stripped:
            return True
        return False
    return False


def _voice_has_executable_main(source: str) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    return any(
        isinstance(node, ast.FunctionDef) and node.name == "main"
        for node in tree.body
    )


def _voice_has_executable_module_code(source: str) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue
        return True
    return False


def resolve_stored_voice_challenge_code(
    challenge_id: str,
    stored: str | None,
    *,
    default: str,
    completed: bool,
) -> str:
    if not isinstance(stored, str) or not stored.strip():
        return default
    challenge = challenge_by_id(challenge_id, level="voice")
    if challenge is not None and _voice_stored_needs_carry_forward(
        challenge,
        stored,
        default=default,
        completed=completed,
    ):
        return default
    if not completed and stored.strip() in _voice_legacy_stored_values(challenge_id):
        return default
    return stored


LOOP_LEGACY_ANSWER_CODES: dict[str, str] = {
    "c1": """def main():
    while True:
        question = input("> ")
        if question == "bye":
            break""",
    "c2": """        if question == "bye":
            break
        response = llm.invoke(f"{prompt}\\n\\n問題：{question}")
        print(response)""",
    "c3": """        if not question.strip():
            continue""",
}


def resolve_stored_lab_code(
    stored: str | None,
    *,
    legacy: str,
    lab_done: bool,
) -> str:
    if lab_done:
        return stored if isinstance(stored, str) else EMPTY_FORGE_LAB_CODE
    if not isinstance(stored, str) or not stored.strip():
        return EMPTY_FORGE_LAB_CODE
    if stored.strip() == legacy.strip():
        return EMPTY_FORGE_LAB_CODE
    return stored


def challenge_by_id(challenge_id: str, *, level: str = "voice") -> ForgeChallenge | None:
    if level == "brain":
        challenges = BRAIN_FORGE_CHALLENGES
    elif level == "loop":
        challenges = LOOP_FORGE_CHALLENGES
    else:
        challenges = VOICE_FORGE_CHALLENGES
    for challenge in challenges:
        if challenge.id == challenge_id:
            return challenge
    return None


def resolve_stored_challenge_code(
    challenge_id: str,
    stored: str | None,
    *,
    default: str,
    completed: bool,
    legacy_map: dict[str, str] | None = None,
) -> str:
    legacy = legacy_map or LEGACY_ANSWER_CODES
    if not isinstance(stored, str) or not stored.strip():
        return default
    if not completed and stored.strip() == legacy.get(challenge_id, "").strip():
        return default
    return stored


def _brain_stored_needs_carry_forward(
    challenge: ForgeChallenge,
    stored: str,
    *,
    default: str,
    completed: bool,
    legacy_map: dict[str, str] | None = None,
) -> bool:
    if completed:
        return False
    stripped = stored.strip()
    if not stripped:
        return True
    if stripped == challenge.default_code.strip():
        return True
    legacy = legacy_map or LEGACY_ANSWER_CODES
    if not completed and stripped == legacy.get(challenge.id, "").strip():
        return True
    if challenge.id == "c1" and stripped == _BRAIN_C1_LEGACY_STARTER:
        return True
    if challenge.id == "c1" and _loop_c1_hint_misplaced(stripped):
        return True
    if challenge.id == "c2" and stripped == _BRAIN_C2_LEGACY_ANSWER.strip():
        return True
    if challenge.id == "c2" and not has_input_call(stripped):
        return True
    if challenge.id == "c3":
        if not has_input_call(stripped) or not has_brain_constructor(stripped):
            return True
        if "invoke" not in stripped and stripped == challenge.default_code.strip():
            return True
    if stripped == default.strip():
        return False
    if challenge.id in {"c2", "c3", "c4"} and stripped == challenge.default_code.strip():
        return True
    return False


def resolve_stored_brain_challenge_code(
    challenge: ForgeChallenge,
    stored: str | None,
    *,
    default: str,
    completed: bool,
    legacy_map: dict[str, str] | None = None,
) -> str:
    if not isinstance(stored, str) or not stored.strip():
        return default
    legacy = legacy_map or LEGACY_ANSWER_CODES
    if not completed and stored.strip() == legacy.get(challenge.id, "").strip():
        return default
    if _brain_stored_needs_carry_forward(
        challenge,
        stored,
        default=default,
        completed=completed,
        legacy_map=legacy_map,
    ):
        return default
    return stored


def _brain_model_literal(source: str) -> str | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Name) or func.id != "Brain":
            continue
        for keyword in node.keywords:
            if keyword.arg == "model":
                arg = keyword.value
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    return arg.value
        if node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                return arg.value
    return None


def _editor_ahead_of_expected(current: str, expected: str) -> bool:
    cur = current.strip()
    exp = expected.strip()
    if not cur:
        return False
    if cur == exp:
        return True
    if has_input_call(cur) and not has_input_call(exp):
        return True
    if has_brain_constructor(cur) and not has_brain_constructor(exp):
        return True
    if _brain_model_literal(cur) and not _brain_model_literal(exp):
        return True
    if "invoke(" in cur.replace(" ", "") and "invoke(" not in exp.replace(" ", ""):
        return True
    if "while True" in cur and "while True" not in exp:
        return True
    if "break" in cur and "break" not in exp:
        return True
    return False


def brain_editor_code_needs_refresh(
    challenge: ForgeChallenge,
    current: str,
    *,
    expected: str,
    completed: bool,
) -> bool:
    if completed:
        return False
    stripped = current.strip()
    if not stripped:
        return True
    if _editor_ahead_of_expected(stripped, expected.strip()):
        return False
    return _brain_stored_needs_carry_forward(
        challenge,
        stripped,
        default=expected,
        completed=False,
    )


def voice_editor_code_needs_refresh(
    challenge: ForgeChallenge,
    current: str,
    *,
    expected: str,
    completed: bool,
) -> bool:
    if completed:
        return False
    stripped = current.strip()
    if not stripped:
        return True
    if stripped == expected.strip():
        return False
    if _voice_stored_needs_carry_forward(
        challenge,
        stripped,
        default=expected,
        completed=completed,
    ):
        return True
    if not completed and stripped != expected.strip() and "speak" in stripped:
        return True
    return False


def forge_editor_code_needs_refresh(
    challenge: ForgeChallenge,
    current: str,
    *,
    expected: str,
    completed: bool,
    level: str,
) -> bool:
    if level == "brain":
        return brain_editor_code_needs_refresh(
            challenge,
            current,
            expected=expected,
            completed=completed,
        )
    if level == "loop":
        return brain_editor_code_needs_refresh(
            challenge,
            current,
            expected=expected,
            completed=completed,
        )
    return voice_editor_code_needs_refresh(
        challenge,
        current,
        expected=expected,
        completed=completed,
    )


def challenge_code_for_persist(
    session_value: str,
    *,
    default: str,
    completed: bool,
) -> str:
    raw = str(session_value)
    if completed or raw.strip():
        return raw
    return default


def voice_highest_challenge_code(challenge_codes: dict[str, str]) -> str:
    for cid in ("c3", "c2", "c1"):
        raw = challenge_codes.get(cid, "").strip()
        if raw:
            return raw
    return ""


def _extract_module_if_name_guard(source: str) -> str:
    lines = source.splitlines()
    for index, line in enumerate(lines):
        if line.strip().startswith("if __name__"):
            return "\n".join(lines[index:]).strip()
    return _VOICE_C3_SUFFIX.strip()


def _append_voice_lab_hint(source: str) -> str:
    if "再加一句自我介紹" in source:
        return source.strip()
    from agent_dungeon.forge.agent_py_store import strip_if_name_guard_blocks

    main_part = strip_if_name_guard_blocks(source.strip())
    guard = _extract_module_if_name_guard(source)
    if not main_part.strip():
        return source.strip()

    lines = main_part.splitlines()
    insert_at = len(lines)
    for index in range(len(lines) - 1, 0, -1):
        line = lines[index]
        if line.strip():
            insert_at = index + 1
            break
    hint_lines = _VOICE_LAB_HINT.splitlines()
    for offset, hint_line in enumerate(hint_lines):
        lines.insert(insert_at + offset, hint_line)
    return f"{'\n'.join(lines).rstrip()}\n\n{guard}"


def voice_forge_lab_seed_code(challenge_codes: dict[str, str]) -> str:
    c3 = challenge_codes.get("c3", "").strip()
    if c3 and _voice_has_executable_main(c3) and has_main_call_in_main_guard(c3):
        return _append_voice_lab_hint(c3)

    c2 = challenge_codes.get("c2", "").strip()
    if c2 and _voice_has_executable_main(c2):
        base = f"{c2.rstrip()}\n\n{_VOICE_C3_SUFFIX.strip()}"
        return _append_voice_lab_hint(base)

    return ""


def _brain_lab_seed_ready(source: str) -> bool:
    stripped = source.strip()
    if not stripped or not _voice_has_executable_main(stripped):
        return False
    if not has_input_call(stripped):
        return False
    if not has_brain_constructor(stripped):
        return False
    return "invoke(" in stripped.replace(" ", "")


def brain_forge_lab_seed_code(challenge_codes: dict[str, str]) -> str:
    c3 = challenge_codes.get("c3", "").strip()
    if c3 and _brain_lab_seed_ready(c3):
        return c3

    c2 = challenge_codes.get("c2", "").strip()
    if c2 and _voice_has_executable_main(c2):
        merged = f"{c2.rstrip()}\n{_BRAIN_C3_SUFFIX.strip()}"
        if _brain_lab_seed_ready(merged):
            return merged

    return ""


def _carry_forward_voice_code(
    challenge: ForgeChallenge,
    *,
    prior_code: str,
) -> str:
    prior = prior_code.strip()
    if not prior:
        return challenge.default_code
    if challenge.id == "c2":
        if _voice_has_executable_main(prior):
            return prior
        return _voice_c2_template_with_prior(prior)
    if challenge.id == "c3":
        suffix = challenge.default_code.strip()
        if _voice_has_executable_main(prior):
            return f"{prior.rstrip()}\n\n{suffix}"
        return challenge.default_code
    suffix = challenge.default_code.strip()
    return f"{prior}\n\n{suffix}"


def challenge_codes_from_stored(
    stored: dict | None,
    *,
    completed: dict[str, bool] | None = None,
) -> dict[str, str]:
    done = completed or {}
    codes: dict[str, str] = {}
    prior = ""
    for index, challenge in enumerate(VOICE_FORGE_CHALLENGES):
        default = challenge.default_code
        if index > 0 and prior and done.get(VOICE_FORGE_CHALLENGES[index - 1].id, False):
            default = _carry_forward_voice_code(challenge, prior_code=prior)
        stored_raw = stored.get(challenge.id) if isinstance(stored, dict) else None
        codes[challenge.id] = resolve_stored_voice_challenge_code(
            challenge.id,
            stored_raw if isinstance(stored_raw, str) else None,
            default=default,
            completed=done.get(challenge.id, False),
        )
        if done.get(challenge.id, False):
            prior = codes[challenge.id]
        elif codes[challenge.id].strip() and not codes[challenge.id].lstrip().startswith("#"):
            prior = codes[challenge.id]
    return codes


def _extract_main_indented_body(source: str) -> str:
    from agent_dungeon.forge.agent_py_store import normalize_to_main_function, strip_if_name_guard_blocks

    text = strip_if_name_guard_blocks(normalize_to_main_function(source.strip()))
    lines = text.splitlines()
    if not lines:
        return ""
    if lines[0].strip().startswith("def main"):
        body_lines = lines[1:]
        return "\n".join(body_lines).rstrip()
    return "\n".join(f"    {line}" if line.strip() else "" for line in lines).rstrip()


def _brain_c1_from_voice_seed(voice_seed: str) -> str:
    seed = voice_seed.strip()
    if not seed or seed.strip() == _EMPTY_MAIN:
        return BRAIN_FORGE_CHALLENGES[0].default_code

    body = _extract_main_indented_body(seed)
    if not body.strip() or body.strip() == "pass":
        return BRAIN_FORGE_CHALLENGES[0].default_code

    return f"def main():\n{_BRAIN_C1_HINT}\n{body}"


def _carry_forward_brain_code(
    challenge: ForgeChallenge,
    *,
    prior_code: str,
) -> str:
    prior = prior_code.strip()
    if not prior:
        return challenge.default_code
    if "def main" not in prior:
        indented = "\n".join(f"    {line}" if line.strip() else "" for line in prior.splitlines())
        prior = f"def main():\n{indented}"
    suffix = challenge.default_code.strip()
    if challenge.id == "c2":
        body = _extract_main_indented_body(prior)
        if not body.strip():
            return f"def main():\n{suffix}"
        return f"def main():\n{suffix}\n{body}"
    return f"{prior.rstrip()}\n{suffix}"


def merge_brain_challenge_stored_with_session(
    stored: dict | None,
    *,
    session_overrides: dict[str, str] | None = None,
    completed: dict[str, bool] | None = None,
) -> dict | None:
    """將 Forge 編輯器 session 內容合併進 stored（含進行中關卡），供 carry-forward 使用。"""
    _ = completed
    if not session_overrides:
        return stored if isinstance(stored, dict) else None
    merged = dict(stored) if isinstance(stored, dict) else {}
    for challenge in BRAIN_FORGE_CHALLENGES:
        raw = session_overrides.get(challenge.id)
        if isinstance(raw, str) and raw.strip():
            merged[challenge.id] = raw
    return merged


def merge_loop_challenge_stored_with_session(
    stored: dict | None,
    *,
    session_overrides: dict[str, str] | None = None,
    completed: dict[str, bool] | None = None,
) -> dict | None:
    """將 Loop Forge 編輯器 session 內容合併進 stored（含進行中關卡）。"""
    _ = completed
    if not session_overrides:
        return stored if isinstance(stored, dict) else None
    merged = dict(stored) if isinstance(stored, dict) else {}
    for challenge in LOOP_FORGE_CHALLENGES:
        raw = session_overrides.get(challenge.id)
        if isinstance(raw, str) and raw.strip():
            merged[challenge.id] = raw
    return merged


def brain_challenge_codes_from_stored(
    stored: dict | None,
    *,
    completed: dict[str, bool] | None = None,
    voice_seed: str = "",
) -> dict[str, str]:
    done = completed or {}
    codes: dict[str, str] = {}
    prior = ""
    for challenge in BRAIN_FORGE_CHALLENGES:
        if challenge.id == "c1" and not prior:
            default = _brain_c1_from_voice_seed(voice_seed)
        elif prior:
            default = _carry_forward_brain_code(challenge, prior_code=prior)
        else:
            default = challenge.default_code
        stored_raw = stored.get(challenge.id) if isinstance(stored, dict) else None
        codes[challenge.id] = resolve_stored_brain_challenge_code(
            challenge,
            stored_raw if isinstance(stored_raw, str) else None,
            default=default,
            completed=done.get(challenge.id, False),
        )
        if done.get(challenge.id, False):
            prior = codes[challenge.id]
        elif codes[challenge.id].strip():
            prior = codes[challenge.id]
    return codes


def _strip_loop_c1_hint(source: str) -> str:
    lines = source.splitlines()
    kept: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if _LOOP_C1_HINT_MARKER in line:
            while index < len(lines) and "Code Here" not in lines[index]:
                index += 1
            if index < len(lines):
                index += 1
            continue
        kept.append(line)
        index += 1
    return "\n".join(kept).rstrip()


def _loop_c1_hint_misplaced(source: str) -> bool:
    stripped = source.strip()
    if _LOOP_C1_HINT_MARKER not in stripped:
        return False
    hint_at = stripped.find("本關")
    if hint_at < 0:
        return False
    llm_at = stripped.find("llm = Brain")
    input_at = stripped.find("input(")
    if llm_at >= 0 and hint_at < llm_at:
        return True
    if input_at >= 0 and hint_at > input_at:
        return True
    return False


def _insert_loop_c1_hint_after_llm(source: str) -> str:
    seed = _strip_loop_c1_hint(source.strip())
    if not seed:
        return f"def main():\n{_LOOP_C1_HINT}"
    if "def main" not in seed:
        seed = f"def main():\n{seed}"

    lines = seed.splitlines()
    insert_at: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("llm = Brain(") or (
            stripped.startswith("llm") and "Brain(" in stripped
        ):
            insert_at = index + 1
            break
    if insert_at is None:
        for index, line in enumerate(lines):
            if line.strip().startswith("def main"):
                insert_at = index + 1
                break
    if insert_at is None:
        return f"{seed.rstrip()}\n{_LOOP_C1_HINT}"

    hint_lines = _LOOP_C1_HINT.splitlines()
    for offset, hint_line in enumerate(hint_lines):
        lines.insert(insert_at + offset, hint_line)
    return "\n".join(lines)


def _loop_c1_from_brain_seed(brain_seed: str) -> str:
    return _insert_loop_c1_hint_after_llm(brain_seed)


def _carry_forward_loop_code(
    challenge: ForgeChallenge,
    *,
    prior_code: str,
    brain_seed: str,
) -> str:
    prior = prior_code.strip()
    if challenge.id == "c1":
        if prior:
            return _insert_loop_c1_hint_after_llm(prior)
        return _loop_c1_from_brain_seed(brain_seed)
    if not prior:
        return _loop_c1_from_brain_seed(brain_seed)
    suffix = challenge.default_code.strip()
    return f"{prior.rstrip()}\n{suffix}"


def loop_challenge_codes_from_stored(
    stored: dict | None,
    *,
    completed: dict[str, bool] | None = None,
    brain_seed: str = "",
) -> dict[str, str]:
    done = completed or {}
    codes: dict[str, str] = {}
    prior = ""
    for challenge in LOOP_FORGE_CHALLENGES:
        default = _carry_forward_loop_code(
            challenge,
            prior_code=prior,
            brain_seed=brain_seed,
        )
        stored_raw = stored.get(challenge.id) if isinstance(stored, dict) else None
        codes[challenge.id] = resolve_stored_brain_challenge_code(
            challenge,
            stored_raw if isinstance(stored_raw, str) else None,
            default=default,
            completed=done.get(challenge.id, False),
            legacy_map=LOOP_LEGACY_ANSWER_CODES,
        )
        if done.get(challenge.id, False):
            prior = codes[challenge.id]
        elif codes[challenge.id].strip():
            prior = codes[challenge.id]
    return codes
