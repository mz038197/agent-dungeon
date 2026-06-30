from __future__ import annotations

from agent_dungeon.forge.challenges import (
    BRAIN_FORGE_CHALLENGES,
    LEGACY_ANSWER_CODES,
    VOICE_FORGE_CHALLENGES,
    brain_challenge_codes_from_stored,
    challenge_code_for_persist,
    challenge_codes_from_stored,
    forge_editor_code_needs_refresh,
    voice_editor_code_needs_refresh,
)
from agent_dungeon.forge.llm_provider import DEFAULT_BRAIN_MODEL


def test_legacy_c1_answer_replaced_with_comment() -> None:
    stored = {"c1": LEGACY_ANSWER_CODES["c1"]}
    codes = challenge_codes_from_stored(stored, completed={"c1": False})
    assert codes["c1"] == VOICE_FORGE_CHALLENGES[0].default_code
    assert 'print("Hello")' not in codes["c1"]


def test_legacy_c1_kept_when_challenge_complete() -> None:
    stored = {"c1": LEGACY_ANSWER_CODES["c1"]}
    codes = challenge_codes_from_stored(stored, completed={"c1": True})
    assert codes["c1"] == LEGACY_ANSWER_CODES["c1"]


def test_user_custom_code_preserved() -> None:
    custom = 'print("Hello")\nprint("more")'
    stored = {"c1": custom}
    codes = challenge_codes_from_stored(stored, completed={"c1": False})
    assert codes["c1"] == custom


def test_empty_stored_uses_comment_defaults() -> None:
    codes = challenge_codes_from_stored(None)
    for challenge in VOICE_FORGE_CHALLENGES:
        assert codes[challenge.id] == challenge.default_code
        assert codes[challenge.id].startswith("#")


def test_c3_legacy_answer_not_replaced_by_c2_stored_code() -> None:
    """c3 正確答案與 LEGACY 相同；不應因 stored 仍是 c2 程式碼而覆寫。"""
    stored = {"c3": LEGACY_ANSWER_CODES["c2"]}
    codes = challenge_codes_from_stored(stored, completed={"c3": False})
    assert codes["c3"] == LEGACY_ANSWER_CODES["c2"]
    assert LEGACY_ANSWER_CODES["c3"] != codes["c3"]


def test_brain_c2_stored_suffix_only_uses_carry_forward() -> None:
    c1_code = 'question = input("q")\nprint(question)'
    stored = {"c1": c1_code, "c2": BRAIN_FORGE_CHALLENGES[1].default_code}
    codes = brain_challenge_codes_from_stored(
        stored,
        completed={"c1": True, "c2": False},
    )
    assert "input(" in codes["c2"]
    assert "Brain(" in codes["c2"]
    assert codes["c2"].startswith(c1_code)


def test_brain_c3_stored_suffix_only_uses_carry_forward() -> None:
    prior = f"""question = input("q")
print(question)

llm = Brain(model="{DEFAULT_BRAIN_MODEL}")"""
    stored = {"c3": BRAIN_FORGE_CHALLENGES[2].default_code}
    codes = brain_challenge_codes_from_stored(
        stored,
        completed={"c1": True, "c2": True, "c3": False},
    )
    assert codes["c3"].count("input(") >= 1
    assert codes["c3"].count("Brain(") >= 1
    assert "invoke" in codes["c3"]


def test_brain_completed_challenge_keeps_custom_stored() -> None:
    custom = 'question = input("x")\nprint("custom")\nllm = Brain(model="x")\nprint("done")'
    stored = {"c2": custom}
    codes = brain_challenge_codes_from_stored(stored, completed={"c2": True})
    assert codes["c2"] == custom


def test_brain_cascade_prior_not_broken_by_bad_c2_stored() -> None:
    c1_code = 'question = input("q")\nprint(question)'
    suffix_only = f'llm = Brain(model="{DEFAULT_BRAIN_MODEL}")'
    stored = {"c1": c1_code, "c2": suffix_only, "c3": BRAIN_FORGE_CHALLENGES[2].default_code}
    codes = brain_challenge_codes_from_stored(
        stored,
        completed={"c1": True, "c2": False, "c3": False},
    )
    assert c1_code in codes["c2"]
    assert "invoke" in codes["c3"]
    assert "input(" in codes["c3"]


def test_empty_stored_voice_c2_uses_default() -> None:
    stored = {"c1": 'print("Hello")', "c2": "", "c3": ""}
    codes = challenge_codes_from_stored(stored, completed={"c1": True, "c2": False, "c3": False})
    assert codes["c2"] == VOICE_FORGE_CHALLENGES[1].default_code
    assert codes["c3"] == VOICE_FORGE_CHALLENGES[2].default_code


def test_voice_editor_refresh_empty_session() -> None:
    challenge = VOICE_FORGE_CHALLENGES[1]
    assert voice_editor_code_needs_refresh(
        challenge,
        "",
        expected=challenge.default_code,
        completed=False,
    )


def test_voice_editor_keeps_user_code() -> None:
    challenge = VOICE_FORGE_CHALLENGES[1]
    custom = "def speak():\n    print('Hello')"
    assert not voice_editor_code_needs_refresh(
        challenge,
        custom,
        expected=challenge.default_code,
        completed=False,
    )


def test_voice_editor_refresh_legacy_answer() -> None:
    challenge = VOICE_FORGE_CHALLENGES[1]
    assert voice_editor_code_needs_refresh(
        challenge,
        LEGACY_ANSWER_CODES["c2"],
        expected=challenge.default_code,
        completed=False,
    )


def test_forge_editor_voice_dispatch() -> None:
    challenge = VOICE_FORGE_CHALLENGES[0]
    assert forge_editor_code_needs_refresh(
        challenge,
        "",
        expected=challenge.default_code,
        completed=False,
        level="voice",
    )


def test_forge_editor_brain_empty_session() -> None:
    challenge = BRAIN_FORGE_CHALLENGES[0]
    assert forge_editor_code_needs_refresh(
        challenge,
        "",
        expected=challenge.default_code,
        completed=False,
        level="brain",
    )


def test_challenge_code_for_persist_empty_incomplete() -> None:
    default = VOICE_FORGE_CHALLENGES[1].default_code
    assert challenge_code_for_persist("", default=default, completed=False) == default


def test_challenge_code_for_persist_keeps_completed_empty() -> None:
    default = VOICE_FORGE_CHALLENGES[1].default_code
    assert challenge_code_for_persist("", default=default, completed=True) == ""
