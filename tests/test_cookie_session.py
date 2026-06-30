from __future__ import annotations

import time

import pytest

from agent_dungeon.auth.cookie_session import (
    AUTH_COOKIE_MAX_AGE_SECONDS,
    AUTH_COOKIE_NAME,
    cookie_browser_options,
    issue_auth_cookie_value,
    parse_auth_cookie_value,
)
from agent_dungeon.auth.session import AuthUser


@pytest.fixture
def auth_user() -> AuthUser:
    return AuthUser(
        google_sub="google-sub-123",
        email="student@example.com",
        name="Student",
    )


def test_issue_and_parse_round_trip(
    monkeypatch: pytest.MonkeyPatch, auth_user: AuthUser
) -> None:
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret")
    token = issue_auth_cookie_value(auth_user)
    assert token is not None
    assert "." in token

    restored = parse_auth_cookie_value(token)
    assert restored == auth_user


def test_parse_rejects_tampered_signature(
    monkeypatch: pytest.MonkeyPatch, auth_user: AuthUser
) -> None:
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret")
    token = issue_auth_cookie_value(auth_user)
    assert token is not None
    encoded, _sig = token.rsplit(".", 1)
    assert parse_auth_cookie_value(f"{encoded}.deadbeef") is None


def test_parse_rejects_expired_token(
    monkeypatch: pytest.MonkeyPatch, auth_user: AuthUser
) -> None:
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret")
    fixed_now = 1_700_000_000.0
    monkeypatch.setattr(time, "time", lambda: fixed_now)
    token = issue_auth_cookie_value(auth_user)
    assert token is not None
    monkeypatch.setattr(
        time,
        "time",
        lambda: fixed_now + AUTH_COOKIE_MAX_AGE_SECONDS + 1,
    )
    assert parse_auth_cookie_value(token) is None


def test_issue_requires_session_secret(
    monkeypatch: pytest.MonkeyPatch, auth_user: AuthUser
) -> None:
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    assert issue_auth_cookie_value(auth_user) is None


def test_cookie_browser_options_secure_on_https(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_URL", "https://dungeon.example.com")
    options = cookie_browser_options()
    assert options["secure"] is True
    assert options["same_site"] == "Lax"
    assert options["max_age"] == AUTH_COOKIE_MAX_AGE_SECONDS


def test_cookie_browser_options_not_secure_on_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_URL", "http://127.0.0.1:8501")
    options = cookie_browser_options()
    assert options["secure"] is False


def test_auth_cookie_name() -> None:
    assert AUTH_COOKIE_NAME == "dungeon_auth"
