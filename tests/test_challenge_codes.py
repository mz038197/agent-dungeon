from __future__ import annotations

import ast

from agent_dungeon.forge.challenges import (
    BRAIN_FORGE_CHALLENGES,
    LEGACY_ANSWER_CODES,
    VOICE_FORGE_CHALLENGES,
    _brain_stored_needs_carry_forward,
    brain_challenge_codes_from_stored,
    challenge_code_for_persist,
    challenge_codes_from_stored,
    forge_editor_code_needs_refresh,
    merge_brain_challenge_stored_with_session,
    voice_editor_code_needs_refresh,
)
from agent_dungeon.forge.code_checks import has_brain_constructor, has_input_call
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
    assert codes["c1"] == VOICE_FORGE_CHALLENGES[0].default_code
    assert codes["c1"].startswith("#")
    assert "本關" in codes["c2"]
    c2_tree = ast.parse(codes["c2"])
    assert not any(isinstance(node, ast.FunctionDef) for node in c2_tree.body)
    assert 'if __name__' in codes["c3"]
    assert codes["c3"] == VOICE_FORGE_CHALLENGES[2].default_code


def test_c3_legacy_answer_not_replaced_by_c2_stored_code() -> None:
    """c3 正確答案與 LEGACY 相同；不應因 stored 仍是 c2 程式碼而覆寫。"""
    stored = {"c3": LEGACY_ANSWER_CODES["c2"]}
    codes = challenge_codes_from_stored(stored, completed={"c3": False})
    assert codes["c3"] == LEGACY_ANSWER_CODES["c2"]
    assert LEGACY_ANSWER_CODES["c3"] != codes["c3"]


def test_brain_c2_carry_forward_uses_session_c1_when_stored_default() -> None:
    c1_code = 'question = input("q")\nprint(question)'
    stored = {"c1": BRAIN_FORGE_CHALLENGES[0].default_code, "c2": BRAIN_FORGE_CHALLENGES[1].default_code}
    completed = {"c1": True, "c2": False}
    merged = merge_brain_challenge_stored_with_session(
        stored,
        session_overrides={"c1": c1_code},
        completed=completed,
    )
    codes = brain_challenge_codes_from_stored(merged, completed=completed)
    assert 'input("q")' in codes["c2"]
    assert "input(" in codes["c2"]
    assert "本關" in codes["c2"]


def test_brain_c2_comment_only_input_does_not_block_carry_forward() -> None:
    c1_code = 'question = input("q")\nprint(question)'
    comment_only_c2 = f"{BRAIN_FORGE_CHALLENGES[0].default_code}\n\n{BRAIN_FORGE_CHALLENGES[1].default_code}"
    stored = {"c1": c1_code, "c2": comment_only_c2}
    codes = brain_challenge_codes_from_stored(
        stored,
        completed={"c1": True, "c2": False},
    )
    assert 'input("q")' in codes["c2"]
    assert "本關" in codes["c2"]


def test_brain_c2_stored_suffix_only_uses_carry_forward() -> None:
    c1_code = 'question = input("q")\nprint(question)'
    stored = {"c1": c1_code, "c2": BRAIN_FORGE_CHALLENGES[1].default_code}
    codes = brain_challenge_codes_from_stored(
        stored,
        completed={"c1": True, "c2": False},
    )
    assert "input(" in codes["c2"]
    assert 'input("q")' in codes["c2"]
    assert f'llm = Brain(model="{DEFAULT_BRAIN_MODEL}")' not in codes["c2"]
    assert "本關" in codes["c2"]


def test_brain_c2_legacy_answer_replaced_with_comment_hint() -> None:
    from agent_dungeon.forge.challenges import _BRAIN_C2_LEGACY_ANSWER

    stored = {"c2": _BRAIN_C2_LEGACY_ANSWER}
    codes = brain_challenge_codes_from_stored(stored, completed={"c2": False})
    assert f'llm = Brain(model="{DEFAULT_BRAIN_MODEL}")' not in codes["c2"]
    assert "llm" in codes["c2"]


def test_brain_c3_stored_suffix_only_uses_carry_forward() -> None:
    c1_code = 'question = input("q")\nprint(question)'
    c2_code = f'{c1_code}\n\nllm = Brain(model="{DEFAULT_BRAIN_MODEL}")'
    stored = {
        "c1": c1_code,
        "c2": c2_code,
        "c3": BRAIN_FORGE_CHALLENGES[2].default_code,
    }
    codes = brain_challenge_codes_from_stored(
        stored,
        completed={"c1": True, "c2": True, "c3": False},
    )
    assert has_input_call(codes["c3"])
    assert has_brain_constructor(codes["c3"])
    assert "invoke" in codes["c3"]
    assert c1_code in codes["c3"] or 'input("q")' in codes["c3"]
    assert f'llm = Brain(model="{DEFAULT_BRAIN_MODEL}")' in codes["c3"]


def test_brain_c3_comment_template_still_needs_carry_forward() -> None:
    c1_code = 'question = input("q")\nprint(question)'
    c2_code = f'{c1_code}\n\nllm = Brain(model="{DEFAULT_BRAIN_MODEL}")'
    template_only = f"{c1_code}\n\n{BRAIN_FORGE_CHALLENGES[1].default_code}\n\n{BRAIN_FORGE_CHALLENGES[2].default_code}"
    challenge = BRAIN_FORGE_CHALLENGES[2]
    default = f"{c2_code}\n\n{challenge.default_code.strip()}"
    assert _brain_stored_needs_carry_forward(
        challenge,
        template_only,
        default=default,
        completed=False,
    )
    assert not has_brain_constructor(template_only)


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
    assert 'input("q")' in codes["c2"]
    assert "invoke" in codes["c3"]
    assert has_input_call(codes["c3"])


def test_voice_c2_legacy_speak_comment_replaced() -> None:
    from agent_dungeon.forge.challenges import VOICE_LEGACY_TEMPLATE_CODES

    stored = {"c2": VOICE_LEGACY_TEMPLATE_CODES["c2"]}
    codes = challenge_codes_from_stored(stored, completed={"c2": False})
    assert "speak" not in codes["c2"].lower()
    assert "本關" in codes["c2"]


def test_voice_c2_legacy_speak_answer_replaced() -> None:
    from agent_dungeon.forge.challenges import VOICE_LEGACY_SPEAK_ANSWER_CODES

    stored = {"c2": VOICE_LEGACY_SPEAK_ANSWER_CODES["c2"]}
    codes = challenge_codes_from_stored(stored, completed={"c2": False})
    assert "speak" not in codes["c2"].lower()
    assert "本關" in codes["c2"]


def test_voice_c2_carry_forward_keeps_c1_print_at_module_level() -> None:
    stored = {"c1": 'print("Hello")', "c2": ""}
    codes = challenge_codes_from_stored(
        stored,
        completed={"c1": True, "c2": False},
    )
    assert "本關" in codes["c2"]
    assert "提示" in codes["c2"]
    assert 'print("Hello")' in codes["c2"]
    assert codes["c2"].index("本關") < codes["c2"].index('print("Hello")')
    c2_tree = ast.parse(codes["c2"])
    assert any(
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        for node in c2_tree.body
    )
    assert not any(isinstance(node, ast.FunctionDef) for node in c2_tree.body)


def test_voice_c2_stored_hint_only_replaced_with_carry_forward() -> None:
    stored = {
        "c1": 'print("Hello")',
        "c2": VOICE_FORGE_CHALLENGES[1].default_code,
    }
    codes = challenge_codes_from_stored(
        stored,
        completed={"c1": True, "c2": False},
    )
    assert 'print("Hello")' in codes["c2"]
    assert codes["c2"].index("本關") < codes["c2"].index('print("Hello")')


def test_voice_editor_refresh_when_session_has_bare_hint() -> None:
    challenge = VOICE_FORGE_CHALLENGES[1]
    expected = f'{challenge.default_code}\n\nprint("Hello")'
    assert voice_editor_code_needs_refresh(
        challenge,
        challenge.default_code,
        expected=expected,
        completed=False,
    )


def test_empty_stored_voice_c2_uses_default() -> None:
    stored = {"c1": 'print("Hello")', "c2": "", "c3": ""}
    codes = challenge_codes_from_stored(
        stored,
        completed={"c1": True, "c2": False, "c3": False},
    )
    assert "本關" in codes["c2"]
    assert "提示" in codes["c2"]
    assert 'print("Hello")' in codes["c2"]
    assert 'if __name__' not in codes["c2"]
    assert codes["c3"] == VOICE_FORGE_CHALLENGES[2].default_code


def test_voice_c3_carry_forward_appends_main_guard() -> None:
    c2_code = 'def main():\n    print("Hello")'
    stored = {"c1": 'print("Hello")', "c2": c2_code, "c3": ""}
    codes = challenge_codes_from_stored(
        stored,
        completed={"c1": True, "c2": True, "c3": False},
    )
    assert c2_code in codes["c3"]
    assert 'if __name__ == "__main__":' in codes["c3"]
    assert "本關" in codes["c3"]


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
    custom = "def main():\n    print('Hello')"
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
