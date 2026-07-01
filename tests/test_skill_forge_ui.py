from __future__ import annotations

from agent_dungeon.core.progress import BRAIN_LEVEL_ID
from agent_dungeon.forge.challenges import BRAIN_FORGE_CHALLENGES, VOICE_FORGE_CHALLENGES
from agent_dungeon.forge.skill_forge_ui import (
    BRAIN_FORGE_CONFIG,
    is_awaiting_collapse,
    review_code_for_completed,
)


def test_review_code_prefers_session_over_default_template() -> None:
    challenge = VOICE_FORGE_CHALLENGES[1]
    student = 'def main():\n    print("Hello")'
    codes = {challenge.id: student}
    assert (
        review_code_for_completed(challenge, codes, challenge.default_code)
        == student
    )


def test_review_code_prefers_session_code() -> None:
    challenge = VOICE_FORGE_CHALLENGES[0]
    codes = {challenge.id: challenge.default_code}
    custom = 'question = input("q")\nprint(question)'
    assert review_code_for_completed(challenge, codes, custom) == custom


def test_review_code_falls_back_to_challenge_codes() -> None:
    challenge = VOICE_FORGE_CHALLENGES[0]
    stored = 'print("Hello")\nprint("more")'
    codes = {challenge.id: stored}
    assert review_code_for_completed(challenge, codes, "") == stored


def test_review_code_falls_back_to_default() -> None:
    challenge = VOICE_FORGE_CHALLENGES[0]
    assert review_code_for_completed(challenge, {}, "") == challenge.default_code


def test_is_awaiting_collapse_false_without_session(monkeypatch) -> None:
    fake_st = type("FakeSt", (), {"session_state": {}})()
    monkeypatch.setattr("agent_dungeon.forge.skill_forge_ui.st", fake_st)
    assert is_awaiting_collapse(BRAIN_FORGE_CONFIG, "c1") is False


def test_is_awaiting_collapse_true_when_flag_set(monkeypatch) -> None:
    fake_st = type("FakeSt", (), {"session_state": {"brain_forge_c1_awaiting_collapse": True}})()
    monkeypatch.setattr("agent_dungeon.forge.skill_forge_ui.st", fake_st)
    assert is_awaiting_collapse(BRAIN_FORGE_CONFIG, "c1") is True


def test_brain_review_prefers_student_code_over_comment_session() -> None:
    challenge = BRAIN_FORGE_CHALLENGES[0]
    student = 'question = input("q")\nprint(question)'
    codes = {challenge.id: student}
    hint_only = challenge.default_code
    assert (
        review_code_for_completed(
            challenge,
            codes,
            hint_only,
            level_id=BRAIN_LEVEL_ID,
        )
        == student
    )


def test_brain_review_uses_session_when_it_has_input_call() -> None:
    challenge = BRAIN_FORGE_CHALLENGES[0]
    student = 'question = input("q")\nprint(question)'
    codes = {challenge.id: challenge.default_code}
    assert (
        review_code_for_completed(
            challenge,
            codes,
            student,
            level_id=BRAIN_LEVEL_ID,
        )
        == student
    )
