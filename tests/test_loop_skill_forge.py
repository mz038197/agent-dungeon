from __future__ import annotations

from agent_dungeon.forge.challenges import LOOP_FORGE_CHALLENGES
from agent_dungeon.forge.loop_skill_forge_ui import LOOP_FORGE_CONFIG


def test_loop_forge_config_challenges() -> None:
    assert LOOP_FORGE_CONFIG.challenges is LOOP_FORGE_CHALLENGES
    assert len(LOOP_FORGE_CONFIG.challenges) == 4


def test_loop_skill_forge_module_imports() -> None:
    from agent_dungeon.forge import loop_skill_forge_ui

    assert hasattr(loop_skill_forge_ui, "render_loop_skill_forge")
