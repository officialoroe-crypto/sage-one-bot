"""HTTP hardening for SAGE ONE: headers, body limits, rate limiting, startup checks.

Pure ASGI middleware (no extra dependencies). Everything here fails closed and is
configured through environment variables documented in SECURITY.md.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque

from config.settings import settings

log = logging.getLogger("sage.security")

SECURITY_HEADERS = {
    b"x-content-type-options": b"nosniff",
    b"x-frame-options": b"DENY",
    b"referrer-policy": b"no-referrer",
    b"permissions-policy": b"camera=(), geolocation=(), payment=(), microphone=(self)",
    b"cross-origin-opener-policy": b"same-origin",
    b"cross-origin-resource-policy": b"same-site",
    # The API only serves JSON; nothing may be loaded or framed from its responses.
    b"content-security-policy": b"default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
    b"cache-control": b"no-store",
}
HSTS = b"max-age=63072000; includeSubDomains"


class SecurityHeadersMiddleware:
    def __init__(self, app, hsts: bool = False):
        self.app = app
        self.hsts = hsts

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = [(k, v) for k, v in message.get("headers", []) if k.lower() not in SECURITY_HEADERS]
                headers.extend(SECURITY_HEADERS.items())
                if self.hsts:
                    headers.append((b"strict-transport-security", HSTS))
                headers = [(k, v) for k, v in headers if k.lower() != b"server"]
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


async def _json_response(send, status: int, detail: str, extra: list | None = None):
    body = json.dumps({"detail": detail}).encode()
    headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]
    headers.extend(extra or [])
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


class BodySizeLimitMiddleware:
    """Reject oversized request bodies (declared or streamed)."""

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        for key, value in scope.get("headers", []):
            if key == b"content-length":
                try:
                    declared = int(value)
                except ValueError:
                    return await _json_response(send, 400, "Invalid Content-Length.")
                if declared > self.max_bytes:
                    return await _json_response(send, 413, "Request body too large.")

        received = 0
        too_big = False

        async def limited_receive():
            nonlocal received, too_big
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    too_big = True
                    return {"type": "http.disconnect"}
            return message

        async def guarded_send(message):
            if too_big:
                return  # discard whatever the app tried to answer; 413 is sent below
            await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except Exception:
            if not too_big:
                raise
        if too_big:
            await _json_response(send, 413, "Request body too large.")


class _Window:
    __slots__ = ("hits",)

    def __init__(self):
        self.hits: deque[float] = deque()


class RateLimiter:
    """Sliding-window limiter, per key. In-memory: one limiter per server process."""

    def __init__(self, limit: int, window: float = 60.0):
        self.limit = limit
        self.window = window
        self._windows: dict[str, _Window] = {}
        self._lock = threading.Lock()
        self._last_sweep = time.monotonic()

    def allow(self, key: str, now: float | None = None) -> tuple[bool, int]:
        now = time.monotonic() if now is None else now
        with self._lock:
            if now - self._last_sweep > self.window:
                cutoff = now - self.window
                for k in [k for k, w in self._windows.items() if not w.hits or w.hits[-1] < cutoff]:
                    del self._windows[k]
                self._last_sweep = now
            win = self._windows.setdefault(key, _Window())
            while win.hits and win.hits[0] <= now - self.window:
                win.hits.popleft()
            if len(win.hits) >= self.limit:
                retry = int(self.window - (now - win.hits[0])) + 1
                return False, max(retry, 1)
            win.hits.append(now)
            return True, 0


def client_ip(scope, trust_proxy: bool) -> str:
    if trust_proxy:
        for key, value in scope.get("headers", []):
            if key == b"x-forwarded-for":
                # The proxy appends the real peer last; earlier entries are client-supplied.
                parts = [p.strip() for p in value.decode("latin-1").split(",") if p.strip()]
                if parts:
                    return parts[-1][:64]
    client = scope.get("client")
    return client[0] if client else "unknown"


class RateLimitMiddleware:
    """Global per-IP limit plus a much tighter limit on login/OTP endpoints."""

    AUTH_PREFIXES = ("/identity/google", "/identity/dev-login", "/identity/phone")

    def __init__(self, app, per_minute: int, auth_per_minute: int, trust_proxy: bool = False):
        self.app = app
        self.trust_proxy = trust_proxy
        self.general = RateLimiter(per_minute)
        self.auth = RateLimiter(auth_per_minute)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") == "OPTIONS":
            return await self.app(scope, receive, send)
        ip = client_ip(scope, self.trust_proxy)
        path = scope.get("path", "")
        limiters = [self.general]
        if path.startswith(self.AUTH_PREFIXES):
            limiters.append(self.auth)
        for limiter in limiters:
            ok, retry = limiter.allow(ip)
            if not ok:
                return await _json_response(
                    send, 429, "Too many requests. Slow down.", [(b"retry-after", str(retry).encode())]
                )
        await self.app(scope, receive, send)


def validate_production_config(cors_origins: list[str]) -> list[str]:
    """Return fatal problems for a production deployment (empty list means OK)."""
    problems: list[str] = []
    if not settings.IS_PRODUCTION:
        return problems
    if not settings.GOOGLE_CLIENT_ID:
        problems.append("GOOGLE_CLIENT_ID is not set.")
    if not settings.OWNER_AUTH_SUBJECT:
        problems.append("SAGE_OWNER_AUTH_SUBJECT is not set (the owner's Google 'sub').")
    if any(o == "*" for o in cors_origins):
        problems.append("SAGE_CORS_ORIGINS must not contain '*'.")
    if any(o.startswith("http://") and "localhost" not in o and "127.0.0.1" not in o for o in cors_origins):
        problems.append("SAGE_CORS_ORIGINS must use https:// origins.")
    return problems
