from __future__ import annotations

from auth.google_oauth import GoogleOAuthService


def test_oauth_state_roundtrip() -> None:
    oauth = GoogleOAuthService(
        client_id="id",
        client_secret="secret",
        redirect_uri="http://127.0.0.1:8501/",
        session_secret="session-secret",
    )
    state = oauth.create_state()
    assert oauth.verify_state(state)
    assert oauth.verify_state(f"  {state}  ")


def test_oauth_state_legacy_colon_format() -> None:
    oauth = GoogleOAuthService(
        client_id="id",
        client_secret="secret",
        redirect_uri="http://127.0.0.1:8501/",
        session_secret="session-secret",
    )
    state = oauth.create_state()
    legacy = oauth._decode_state_candidates(state)[-1]
    assert oauth.verify_state(legacy)


def test_authorize_url_contains_client() -> None:
    oauth = GoogleOAuthService(
        client_id="my-client",
        client_secret="secret",
        redirect_uri="http://127.0.0.1:8501/",
        session_secret="session-secret",
    )
    url = oauth.authorize_url("abc:123:sig")
    assert "client_id=my-client" in url
    assert "redirect_uri=" in url
