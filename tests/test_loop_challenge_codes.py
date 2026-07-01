from __future__ import annotations

from agent_dungeon.forge.challenges import (
    LOOP_FORGE_CHALLENGES,
    LOOP_LEGACY_ANSWER_CODES,
    loop_challenge_codes_from_stored,
)


def test_loop_c1_default_from_brain_seed() -> None:
    brain = """def main():
    llm = Brain(model="gpt-4.1-mini")
    question = input("> ")
    print(question)
"""
    codes = loop_challenge_codes_from_stored(None, completed={}, brain_seed=brain)
    assert "while" in codes["c1"].lower() or "while True" in codes["c1"]
    assert "def main()" in codes["c1"]


def test_loop_legacy_c1_stripped() -> None:
    stored = {"c1": LOOP_LEGACY_ANSWER_CODES["c1"]}
    codes = loop_challenge_codes_from_stored(stored, completed={"c1": False}, brain_seed="")
    assert "while True:" not in codes["c1"] or "#" in codes["c1"]


def test_loop_four_challenge_ids() -> None:
    assert tuple(c.id for c in LOOP_FORGE_CHALLENGES) == ("c1", "c2", "c3", "c4")


def test_loop_c2_carry_forward() -> None:
    c1 = """def main():
    while True:
        question = input("> ")
"""
    stored = {"c1": c1}
    codes = loop_challenge_codes_from_stored(
        stored,
        completed={"c1": True, "c2": False},
        brain_seed="",
    )
    assert "bye" in codes["c2"].lower()
    assert c1.strip() in codes["c2"]
