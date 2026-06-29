from __future__ import annotations

from dataclasses import dataclass

CHALLENGE_IDS = ("c1", "c2", "c3")


@dataclass(frozen=True)
class ForgeChallenge:
    id: str
    label: str
    title: str
    default_code: str


VOICE_FORGE_CHALLENGES: tuple[ForgeChallenge, ...] = (
    ForgeChallenge(
        id="c1",
        label="Challenge 1",
        title="認識 print()",
        default_code='# 使用 print 函式 輸出 "Hello" !',
    ),
    ForgeChallenge(
        id="c2",
        label="Challenge 2",
        title="建立 function",
        default_code='# 定義 speak() 函式，在函式內輸出 Hello',
    ),
    ForgeChallenge(
        id="c3",
        label="Final Challenge",
        title="讓 Agent 說話！",
        default_code='# 定義 speak() 函式，並呼叫 speak() 輸出 Hello!（記得驚嘆號）',
    ),
)


def challenge_by_id(challenge_id: str) -> ForgeChallenge | None:
    for challenge in VOICE_FORGE_CHALLENGES:
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
