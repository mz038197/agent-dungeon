from __future__ import annotations

from dataclasses import dataclass

from agent_dungeon.forge.code_checks import has_input_call
from agent_dungeon.forge.llm_provider import DEFAULT_BRAIN_MODEL

CHALLENGE_IDS = ("c1", "c2", "c3")

VOICE_FORGE_CHALLENGE_IDS = CHALLENGE_IDS
BRAIN_FORGE_CHALLENGE_IDS = CHALLENGE_IDS
LOOP_FORGE_CHALLENGE_IDS = CHALLENGE_IDS

_BRAIN_C1_LEGACY_STARTER = """# 讀取使用者輸入
question = input("你想問什麼？ ")
print(question)
""".strip()


@dataclass(frozen=True)
class ForgeChallenge:
    id: str
    label: str
    title: str
    default_code: str
    editor_hint: str = ""


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
        title="建立 function",
        default_code='# 定義 speak() 函式，在函式內輸出 Hello',
        editor_hint="定義 speak() 函式，在函式內輸出 Hello",
    ),
    ForgeChallenge(
        id="c3",
        label="Final Challenge",
        title="讓 Agent 說話！",
        default_code='# 定義 speak() 函式，並呼叫 speak() 輸出 Hello!（記得驚嘆號）',
        editor_hint="定義 speak() 函式，並呼叫 speak() 輸出 Hello!（記得驚嘆號）",
    ),
)

_BRAIN_C2_SUFFIX = """# --- 本關：建立 Brain（選一個 model）---
# 在此建立 Brain，例如：llm = Brain(model="...")"""

_BRAIN_C2_LEGACY_ANSWER = f"""# --- 本關：建立 Brain（選一個 model）---
llm = Brain(model="{DEFAULT_BRAIN_MODEL}")"""

_BRAIN_C3_SUFFIX = """# --- 本關：完成 Brain 安裝 ---
# 呼叫 llm.invoke(question)，並 print Brain 的回覆
response = llm.invoke(question)
print(response)"""

BRAIN_FORGE_CHALLENGES: tuple[ForgeChallenge, ...] = (
    ForgeChallenge(
        id="c1",
        label="Challenge 1",
        title="讀取使用者輸入",
        default_code="# 讀取使用者輸入：用 input() 取得 question，再用 print 顯示讀到的內容",
        editor_hint="用 input() 讀取問題，再用 print 顯示 input() 讀到的內容",
    ),
    ForgeChallenge(
        id="c2",
        label="Challenge 2",
        title="建立 Brain",
        default_code=_BRAIN_C2_SUFFIX,
        editor_hint='在上方程式碼下方，建立 Brain（llm = Brain(model="...")）',
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

VOICE_LEGACY_LAB_CODE = """def speak():
    print("Hello, I am your AI assistant!")
    print("Nice to meet you!")

speak()
""".strip()

_BRAIN_LEGACY_LAB_PROMPT = "你是一位英文助教，用簡單英文回答。"

BRAIN_LEGACY_LAB_CODE = f"""prompt = "{_BRAIN_LEGACY_LAB_PROMPT}"
llm = Brain(model="{DEFAULT_BRAIN_MODEL}")
question = input("你想問什麼？ ")
response = llm.invoke(f"{{prompt}}\\n\\n問題：{{question}}")
print(response)
""".strip()

_LOOP_C1_SUFFIX = """def main():
    # --- 本關：用 while True 包住 Brain 對話邏輯 ---
    while True:
        question = input("> ")
        if question == "bye":
            break
        # ↓ 在此放入 Brain 的 prompt / llm / invoke / print
"""

_LOOP_C2_SUFFIX = """        response = llm.invoke(f"{prompt}\\n\\n問題：{question}")
        print(response)
"""

_LOOP_C3_CONTINUE_HINT = """        if not question.strip():
            continue
"""

LOOP_FORGE_CHALLENGES: tuple[ForgeChallenge, ...] = (
    ForgeChallenge(
        id="c1",
        label="Challenge 1",
        title="建立對話迴圈",
        default_code=_LOOP_C1_SUFFIX.strip(),
        editor_hint="用 while True 包住 Brain 對話；加上 bye → break，才能在終端機試多輪",
    ),
    ForgeChallenge(
        id="c2",
        label="Challenge 2",
        title="連續問答",
        default_code=_LOOP_C2_SUFFIX.strip(),
        editor_hint="在迴圈內完成 invoke + print，並在終端機至少聊 2 輪",
    ),
    ForgeChallenge(
        id="c3",
        label="Final Challenge",
        title="完善控制流",
        default_code=_LOOP_C3_CONTINUE_HINT.strip(),
        editor_hint="空字串 continue；在終端機試空 Enter 不當成新問題",
    ),
)

LOOP_LEGACY_LAB_CODE = f"""def main():
    prompt = "你是一位友善助教。"
    llm = Brain(model="{DEFAULT_BRAIN_MODEL}")
    while True:
        question = input("> ")
        if question == "bye":
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


if __name__ == "__main__":
    main()
""".strip()


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


# 舊版預設含答案；未完成關卡若仍存這些內容，改回現行註解提示。
LEGACY_ANSWER_CODES: dict[str, str] = {
    "c1": 'print("Hello")',
    "c2": 'def speak():\n    print("Hello")\n\nspeak()',
    "c3": 'def speak():\n    print("Hello!")\n\nspeak()',
}


def resolve_stored_challenge_code(
    challenge_id: str,
    stored: str | None,
    *,
    default: str,
    completed: bool,
) -> str:
    if not isinstance(stored, str) or not stored.strip():
        return default
    if not completed and stored == LEGACY_ANSWER_CODES.get(challenge_id):
        return default
    return stored


def _brain_stored_needs_carry_forward(
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
    if stripped == challenge.default_code.strip():
        return True
    if challenge.id == "c1" and stripped == _BRAIN_C1_LEGACY_STARTER:
        return True
    if challenge.id == "c2" and stripped == _BRAIN_C2_LEGACY_ANSWER.strip():
        return True
    if challenge.id == "c2" and not has_input_call(stripped):
        return True
    if challenge.id == "c3":
        if not has_input_call(stripped) or "Brain(" not in stripped:
            return True
        if "invoke" not in stripped and stripped == challenge.default_code.strip():
            return True
    if stripped == default.strip():
        return False
    if challenge.id in {"c2", "c3"} and stripped == challenge.default_code.strip():
        return True
    return False


def resolve_stored_brain_challenge_code(
    challenge: ForgeChallenge,
    stored: str | None,
    *,
    default: str,
    completed: bool,
) -> str:
    if not isinstance(stored, str) or not stored.strip():
        return default
    if not completed and stored == LEGACY_ANSWER_CODES.get(challenge.id):
        return default
    if _brain_stored_needs_carry_forward(
        challenge,
        stored,
        default=default,
        completed=completed,
    ):
        return default
    return stored


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
    if "#" not in stripped:
        return True
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
    if stripped == LEGACY_ANSWER_CODES.get(challenge.id):
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


def challenge_codes_from_stored(
    stored: dict | None,
    *,
    completed: dict[str, bool] | None = None,
) -> dict[str, str]:
    codes = {challenge.id: challenge.default_code for challenge in VOICE_FORGE_CHALLENGES}
    done = completed or {}
    if not isinstance(stored, dict):
        return codes
    for challenge in VOICE_FORGE_CHALLENGES:
        codes[challenge.id] = resolve_stored_challenge_code(
            challenge.id,
            stored.get(challenge.id),
            default=challenge.default_code,
            completed=done.get(challenge.id, False),
        )
    return codes


def _carry_forward_brain_code(
    challenge: ForgeChallenge,
    *,
    prior_code: str,
) -> str:
    prior = prior_code.strip()
    if not prior:
        return challenge.default_code
    suffix = challenge.default_code.strip()
    return f"{prior}\n\n{suffix}"


def merge_brain_challenge_stored_with_session(
    stored: dict | None,
    *,
    session_overrides: dict[str, str] | None = None,
    completed: dict[str, bool] | None = None,
) -> dict | None:
    """將已完成關卡的 session 編輯器內容合併進 stored，供 carry-forward 使用。"""
    if not session_overrides:
        return stored if isinstance(stored, dict) else None
    done = completed or {}
    merged = dict(stored) if isinstance(stored, dict) else {}
    for challenge in BRAIN_FORGE_CHALLENGES:
        raw = session_overrides.get(challenge.id)
        if not isinstance(raw, str) or not raw.strip():
            continue
        if done.get(challenge.id, False):
            merged[challenge.id] = raw
    return merged


def brain_challenge_codes_from_stored(
    stored: dict | None,
    *,
    completed: dict[str, bool] | None = None,
) -> dict[str, str]:
    done = completed or {}
    codes: dict[str, str] = {}
    prior = ""
    for challenge in BRAIN_FORGE_CHALLENGES:
        default = (
            _carry_forward_brain_code(challenge, prior_code=prior)
            if prior
            else challenge.default_code
        )
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


def _carry_forward_loop_code(
    challenge: ForgeChallenge,
    *,
    prior_code: str,
    brain_seed: str,
) -> str:
    prior = prior_code.strip()
    if challenge.id == "c1":
        if prior:
            return prior
        base = _LOOP_C1_SUFFIX.strip()
        if brain_seed.strip():
            return f"{base}\n        # （參考 Brain 模組）\n"
        return base
    if not prior:
        return challenge.default_code
    suffix = challenge.default_code.strip()
    return f"{prior}\n{suffix}"


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
        default = (
            _carry_forward_loop_code(challenge, prior_code=prior, brain_seed=brain_seed)
            if prior or challenge.id == "c1"
            else challenge.default_code
        )
        if challenge.id == "c1" and not prior:
            default = _carry_forward_loop_code(
                challenge,
                prior_code="",
                brain_seed=brain_seed,
            )
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
