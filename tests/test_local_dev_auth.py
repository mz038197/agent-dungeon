from __future__ import annotations

import os

import pytest

from agent_dungeon.auth.session import (
    default_dev_user,
    local_dev_auth_bypass,
    oauth_enabled,
)


@pytest.fixture(autouse=True)
def _clear_local_dev_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "LOCAL_DEV_AUTH",
        "LOCAL_DEV_EMAIL",
        "LOCAL_DEV_NAME",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "SESSION_SECRET",
    ):
        monkeypatch.delenv(key, raising=False)


def test_local_dev_auth_bypass_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("agent_dungeon.auth.session.load_local_env", lambda: None)
    assert local_dev_auth_bypass() is False
    monkeypatch.setenv("LOCAL_DEV_AUTH", "bypass")
    assert local_dev_auth_bypass() is True
    monkeypatch.setenv("LOCAL_DEV_AUTH", "yes")
    assert local_dev_auth_bypass() is False


def test_oauth_disabled_when_bypass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("agent_dungeon.auth.session.load_local_env", lambda: None)
    monkeypatch.setenv("LOCAL_DEV_AUTH", "bypass")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    monkeypatch.setenv("SESSION_SECRET", "session-secret")
    assert oauth_enabled() is False


def test_default_dev_user_uses_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOCAL_DEV_EMAIL", "alice@example.com")
    monkeypatch.setenv("LOCAL_DEV_NAME", "Alice")
    claims = default_dev_user()
    assert claims.email == "alice@example.com"
    assert claims.name == "Alice"
    assert claims.google_sub.startswith("dev-")


def test_default_dev_user_fallback() -> None:
    claims = default_dev_user()
    assert claims.email == "dev@local.test"
    assert claims.name == "本地開發者"
