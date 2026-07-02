from __future__ import annotations


def test_brain_skill_forge_module_imports() -> None:
    from agent_dungeon.forge import brain_skill_forge_ui

    assert hasattr(brain_skill_forge_ui, "render_brain_skill_forge")
    assert hasattr(brain_skill_forge_ui, "BRAIN_FORGE_CONFIG")
