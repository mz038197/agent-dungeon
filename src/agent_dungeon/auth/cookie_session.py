from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

from agent_dungeon.auth.session import AuthUser, public_url

AUTH_COOKIE_NAME = "dungeon_auth"
AUTH_COOKIE_MAX_AGE_SECONDS = 7 * 24 * 3600


def _session_secret() -> str:
    return os.environ.get("SESSION_SECRET", "").strip()


def _encode_payload(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")


def _decode_payload(encoded: str) -> dict[str, object] | None:
    try:
        padded = encoded + "=" * (-len(encoded) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _sign(encoded: str, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        encoded.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def issue_auth_cookie_value(user: AuthUser) -> str | None:
    secret = _session_secret()
    if not secret:
        return None
    exp = int(time.time()) + AUTH_COOKIE_MAX_AGE_SECONDS
    encoded = _encode_payload(
        {
            "sub": user.google_sub,
            "email": user.email,
            "name": user.name,
            "exp": exp,
        }
    )
    return f"{encoded}.{_sign(encoded, secret)}"


def parse_auth_cookie_value(value: str) -> AuthUser | None:
    secret = _session_secret()
    if not secret or not value:
        return None
    token = value.strip()
    if "." not in token:
        return None
    encoded, sig = token.rsplit(".", 1)
    if not encoded or not sig:
        return None
    expected = _sign(encoded, secret)
    if not hmac.compare_digest(expected.lower(), sig.strip().lower()):
        return None

    payload = _decode_payload(encoded)
    if payload is None:
        return None
    try:
        exp = int(payload.get("exp", 0))
    except (TypeError, ValueError):
        return None
    if exp <= int(time.time()):
        return None

    sub = str(payload.get("sub", "")).strip()
    email = str(payload.get("email", "")).strip()
    name = str(payload.get("name", "")).strip()
    if not sub or not email:
        return None
    return AuthUser(google_sub=sub, email=email, name=name or email)


def cookie_browser_options() -> dict[str, object]:
    secure = public_url().startswith("https://")
    return {
        "max_age": AUTH_COOKIE_MAX_AGE_SECONDS,
        "path": "/",
        "secure": secure,
        "same_site": "Lax",
    }
