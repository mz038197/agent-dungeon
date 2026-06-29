from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass

from auth.google_oauth import GoogleOAuthService, GoogleUserClaims


AUTH_SESSION_KEY = "auth_user"
OAUTH_STATE_KEY = "oauth_state"


@dataclass(frozen=True)
class AuthUser:
    google_sub: str
    email: str
    name: str


def public_url() -> str:
    return os.environ.get("PUBLIC_URL", "http://127.0.0.1:8501").rstrip("/")


def oauth_redirect_uri() -> str:
    explicit = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "").strip()
    if explicit:
        return explicit.rstrip("/") + "/"
    return f"{public_url()}/"


def build_oauth_service() -> GoogleOAuthService:
    return GoogleOAuthService(
        client_id=os.environ.get("GOOGLE_CLIENT_ID", ""),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", ""),
        redirect_uri=oauth_redirect_uri(),
        session_secret=os.environ.get("SESSION_SECRET", ""),
    )


def oauth_enabled() -> bool:
    return build_oauth_service().is_configured()


def get_auth_user(session_state) -> AuthUser | None:
    raw = session_state.get(AUTH_SESSION_KEY)
    if not isinstance(raw, dict):
        return None
    sub = str(raw.get("google_sub", "")).strip()
    email = str(raw.get("email", "")).strip()
    name = str(raw.get("name", "")).strip()
    if not sub or not email:
        return None
    return AuthUser(google_sub=sub, email=email, name=name or email)


def set_auth_user(session_state, claims: GoogleUserClaims) -> AuthUser:
    user = AuthUser(google_sub=claims.google_sub, email=claims.email, name=claims.name)
    session_state[AUTH_SESSION_KEY] = {
        "google_sub": user.google_sub,
        "email": user.email,
        "name": user.name,
    }
    return user


def clear_auth(session_state) -> None:
    session_state.pop(AUTH_SESSION_KEY, None)
    session_state.pop(OAUTH_STATE_KEY, None)


def dev_login(email: str, name: str) -> GoogleUserClaims:
    normalized = email.strip().lower()
    if not normalized or "@" not in normalized:
        raise ValueError("請輸入有效的 email")
    display = name.strip() or normalized.split("@", 1)[0]
    sub = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]
    return GoogleUserClaims(email=normalized, name=display, google_sub=f"dev-{sub}")


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
