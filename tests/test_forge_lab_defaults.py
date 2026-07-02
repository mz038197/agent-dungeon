from __future__ import annotations

from agent_dungeon.forge.challenges import (
    BRAIN_LEGACY_LAB_CODE,
    EMPTY_FORGE_LAB_CODE,
    VOICE_LEGACY_LAB_CODE,
    brain_forge_lab_seed_code,
    resolve_stored_lab_code,
    voice_forge_lab_seed_code,
)
from agent_dungeon.forge.llm_provider import DEFAULT_BRAIN_MODEL


def test_resolve_returns_empty_when_unstored() -> None:
    assert (
        resolve_stored_lab_code(None, legacy=VOICE_LEGACY_LAB_CODE, lab_done=False)
        == EMPTY_FORGE_LAB_CODE
    )


def test_resolve_clears_legacy_voice_starter_when_lab_incomplete() -> None:
    assert (
        resolve_stored_lab_code(
            VOICE_LEGACY_LAB_CODE,
            legacy=VOICE_LEGACY_LAB_CODE,
            lab_done=False,
        )
        == EMPTY_FORGE_LAB_CODE
    )


def test_resolve_clears_legacy_brain_starter_when_lab_incomplete() -> None:
    assert (
        resolve_stored_lab_code(
            BRAIN_LEGACY_LAB_CODE,
            legacy=BRAIN_LEGACY_LAB_CODE,
            lab_done=False,
        )
        == EMPTY_FORGE_LAB_CODE
    )


def test_resolve_keeps_student_draft_when_lab_incomplete() -> None:
    draft = 'def speak():\n    print("my draft")\n'
    assert (
        resolve_stored_lab_code(draft, legacy=VOICE_LEGACY_LAB_CODE, lab_done=False)
        == draft
    )


def test_resolve_keeps_legacy_after_lab_complete() -> None:
    assert (
        resolve_stored_lab_code(
            VOICE_LEGACY_LAB_CODE,
            legacy=VOICE_LEGACY_LAB_CODE,
            lab_done=True,
        )
        == VOICE_LEGACY_LAB_CODE
    )


def test_resolve_keeps_custom_code_after_lab_complete() -> None:
    custom = 'def speak():\n    print("done")\n    print("ok")\nspeak()\n'
    assert (
        resolve_stored_lab_code(custom, legacy=VOICE_LEGACY_LAB_CODE, lab_done=True)
        == custom
    )


def test_voice_forge_lab_seed_has_hint_not_second_print() -> None:
    c3 = """def main():
    print("Hello")

if __name__ == "__main__":
    main()
"""
    seed = voice_forge_lab_seed_code({"c3": c3})
    assert "再加一句自我介紹" in seed
    assert seed.count('print("Hello")') == 1


def test_brain_forge_lab_seed_from_c3() -> None:
    c3 = f'''def main():
    question = input("你想問什麼？ ")
    llm = Brain(model="{DEFAULT_BRAIN_MODEL}")
    response = llm.invoke(question)
    print(response)
'''
    seed = brain_forge_lab_seed_code({"c3": c3})
    assert seed.strip() == c3.strip()
    assert "invoke(" in seed
    assert "Brain(" in seed


def test_brain_forge_lab_seed_empty_without_c3() -> None:
    assert brain_forge_lab_seed_code({}) == ""
    assert brain_forge_lab_seed_code({"c1": 'def main():\n    pass'}) == ""
