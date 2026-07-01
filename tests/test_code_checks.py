from __future__ import annotations

from agent_dungeon.forge.challenges import BRAIN_FORGE_CHALLENGES
from agent_dungeon.forge.code_checks import has_input_call


def test_has_input_call_detects_real_call() -> None:
    assert has_input_call('question = input("q")')


def test_has_input_call_ignores_comment() -> None:
    assert not has_input_call(BRAIN_FORGE_CHALLENGES[0].default_code)
