from __future__ import annotations

from agent_dungeon.forge.challenges import (
    LEGACY_ANSWER_CODES,
    VOICE_FORGE_CHALLENGES,
    challenge_codes_from_stored,
)


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
