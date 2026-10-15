"""Trusted identity verification for SAGE ONE."""

from __future__ import annotations

import hashlib
import secrets
import time
from typing import Any

from fastapi import HTTPException, Request
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from config.settings import settings
from identity.profile import get_profile, upsert_profile

_DEV_SESSIONS: dict[str, dict[str, Any]] = {}
_DEV_SESSION_TTL_SECONDS = 12 * 3600


def _is_local_request(request: Request) -> bool:
    host = request.client.host if request.client else None
    return host in {"127.0.0.1", "::1", "localhost"}


def create_developer_session(label: str = "local-owner") -> tuple[str, dict[str, Any]]:
    if not settings.DEVELOPER_MODE:
        raise HTTPException(status_code=404, detail="Developer mode is disabled.")

    normalized_label = label.strip() or "local-owner"
    if len(normalized_label) > 100:
        raise HTTPException(status_code=422, detail="Developer identity is invalid.")

    subject = hashlib.sha256(normalized_label.encode()).hexdigest()
    claims = {
        "auth_provider": "developer",
        "auth_subject": f"dev:{subject}",
        "developer_label": normalized_label,
        "email": None,
        "email_verified": False,
        "name": "SAGE Owner",
        "developer_mode": True,
        "owner_mode": True,
    }
    token = f"sage-dev-{secrets.token_urlsafe(32)}"
    now = time.time()
    for stale in [t for t, c in _DEV_SESSIONS.items() if c.get("_expires_at", 0) <= now]:
        del _DEV_SESSIONS[stale]
    _DEV_SESSIONS[token] = {**claims, "_expires_at": now + _DEV_SESSION_TTL_SECONDS}
    return token, claims


def verify_google_id_token(raw_token: str) -> dict[str, Any]:
    if not raw_token or not raw_token.strip():
        raise HTTPException(status_code=401, detail="Google ID token is required.")
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google authentication is not configured.")

    try:
        claims = id_token.verify_oauth2_token(
            raw_token.strip(), google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid Google ID token.") from exc
    except Exception as exc:  # e.g. Google's key endpoint unreachable
        raise HTTPException(status_code=503, detail="Identity provider unavailable. Try again.") from exc

    subject = claims.get("sub")
    issuer = claims.get("iss")
    if not subject or issuer not in {"accounts.google.com", "https://accounts.google.com"}:
        raise HTTPException(status_code=401, detail="Invalid Google identity claims.")

    if settings.ENVIRONMENT == "production":
        if not settings.OWNER_AUTH_SUBJECT:
            raise HTTPException(
                status_code=503,
                detail="Production owner identity is not configured.",
            )
        if str(subject) != settings.OWNER_AUTH_SUBJECT:
            raise HTTPException(
                status_code=403,
                detail="This SAGE ONE deployment is restricted to its configured owner.",
            )

    return {
        "auth_provider": "google",
        "auth_subject": str(subject),
        "email": claims.get("email"),
        "email_verified": bool(claims.get("email_verified")),
        "name": claims.get("name"),
        "picture": claims.get("picture"),
        "owner_mode": bool(settings.OWNER_AUTH_SUBJECT and str(subject) == settings.OWNER_AUTH_SUBJECT),
    }


def authenticate_request(request: Request) -> dict[str, Any]:
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Bearer identity token required.")

    if token.startswith("sage-dev-"):
        if not settings.DEVELOPER_MODE or not _is_local_request(request):
            raise HTTPException(status_code=401, detail="Developer session is not available here.")
        stored = _DEV_SESSIONS.get(token)
        if stored is None or stored.get("_expires_at", 0) <= time.time():
            _DEV_SESSIONS.pop(token, None)
            raise HTTPException(status_code=401, detail="Developer session expired. Sign in again.")
        return {k: v for k, v in stored.items() if not k.startswith("_")}

    return verify_google_id_token(token)


def get_or_create_authenticated_profile(claims: dict[str, Any]) -> dict[str, Any]:
    existing = get_profile(claims["auth_provider"], claims["auth_subject"])
    if existing:
        return upsert_profile(
            auth_provider=claims["auth_provider"],
            auth_subject=claims["auth_subject"],
            email=claims.get("email"),
            name=claims.get("name"),
        )

    return upsert_profile(
        auth_provider=claims["auth_provider"],
        auth_subject=claims["auth_subject"],
        email=claims.get("email"),
        name=claims.get("name"),
    )
