from __future__ import annotations

import pytest

from cloud_paths import paths_for_user, user_root


@pytest.fixture
def peas_home(tmp_path, monkeypatch):
    home = tmp_path / "data"
    monkeypatch.setenv("PEAS_AGENT_HOME", str(home))
    return home


def test_different_subs_get_different_dirs(peas_home) -> None:
    a = paths_for_user("sub-a")
    b = paths_for_user("sub-b")
    assert a.root != b.root
    assert a.sessions != b.sessions
    assert user_root("sub-a") == peas_home / "users" / "sub-a"
