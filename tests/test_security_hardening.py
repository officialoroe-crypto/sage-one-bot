import asyncio
import importlib

import pytest
from fastapi.testclient import TestClient

from app.security import (
    BodySizeLimitMiddleware,
    RateLimiter,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    client_ip,
    validate_production_config,
)
from identity.otp import OTPManager, OTPRateLimited
from config.settings import settings


def test_rate_limiter_blocks_then_recovers():
    rl = RateLimiter(3, window=60)
    assert [rl.allow("a", now=t)[0] for t in (0, 1, 2)] == [True] * 3
    ok, retry = rl.allow("a", now=3)
    assert not ok and retry >= 1
    assert rl.allow("b", now=3)[0]            # other clients unaffected
    assert rl.allow("a", now=61)[0]           # window slides


def _asgi_app(status=200):
    async def app(scope, receive, send):
        body = b""
        while True:
            m = await receive()
            if m["type"] != "http.request":
                break
            body += m.get("body", b"")
            if not m.get("more_body"):
                break
        await send({"type": "http.response.start", "status": status, "headers": [(b"server", b"x")]})
        await send({"type": "http.response.body", "body": b"ok"})
    return app


def _call(app, headers=None, body=b"", path="/", client=("1.2.3.4", 1)):
    out = {}
    scope = {"type": "http", "method": "POST", "path": path, "headers": headers or [], "client": client}
    sent = [False]

    async def receive():
        if not sent[0]:
            sent[0] = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(m):
        if m["type"] == "http.response.start":
            out["status"] = m["status"]
            out["headers"] = dict(m["headers"])

    asyncio.run(app(scope, receive, send))
    return out


def test_security_headers_added_and_server_removed():
    out = _call(SecurityHeadersMiddleware(_asgi_app(), hsts=True))
    h = out["headers"]
    assert h[b"x-content-type-options"] == b"nosniff"
    assert h[b"x-frame-options"] == b"DENY"
    assert b"frame-ancestors 'none'" in h[b"content-security-policy"]
    assert b"strict-transport-security" in h
    assert b"server" not in h


def test_body_limit_declared_and_streamed():
    app = BodySizeLimitMiddleware(_asgi_app(), max_bytes=10)
    assert _call(app, headers=[(b"content-length", b"11")], body=b"x" * 11)["status"] == 413
    assert _call(app, headers=[], body=b"x" * 50)["status"] == 413      # no declared length
    assert _call(app, headers=[(b"content-length", b"abc")])["status"] == 400
    assert _call(app, headers=[(b"content-length", b"5")], body=b"hello")["status"] == 200


def test_rate_limit_middleware_auth_paths_stricter():
    app = RateLimitMiddleware(_asgi_app(), per_minute=100, auth_per_minute=2)
    codes = [_call(app, path="/identity/google")["status"] for _ in range(4)]
    assert codes == [200, 200, 429, 429]
    assert _call(app, path="/health")["status"] == 200


def test_forwarded_for_only_trusted_behind_proxy_and_uses_last_hop():
    scope = {"headers": [(b"x-forwarded-for", b"6.6.6.6, 9.9.9.9")], "client": ("10.0.0.1", 1)}
    assert client_ip(scope, trust_proxy=False) == "10.0.0.1"
    assert client_ip(scope, trust_proxy=True) == "9.9.9.9"   # spoofed first entry ignored


def test_production_config_validation(monkeypatch):
    monkeypatch.setattr(settings, "IS_PRODUCTION", True)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", None)
    monkeypatch.setattr(settings, "OWNER_AUTH_SUBJECT", None)
    problems = validate_production_config(["*", "http://evil.example"])
    assert len(problems) == 4
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "id")
    monkeypatch.setattr(settings, "OWNER_AUTH_SUBJECT", "123")
    assert validate_production_config(["https://app.example"]) == []
    monkeypatch.setattr(settings, "IS_PRODUCTION", False)
    assert validate_production_config(["*"]) == []


def test_production_disables_dev_mode_and_docs(monkeypatch):
    monkeypatch.setenv("SAGE_ENV", "production")
    monkeypatch.setenv("SAGE_DEV_MODE", "true")
    monkeypatch.setenv("SAGE_PRIVATE_MODE", "true")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "id")
    monkeypatch.setenv("SAGE_OWNER_AUTH_SUBJECT", "123")
    monkeypatch.setenv("SAGE_CORS_ORIGINS", "https://app.example")
    import config.settings as cs
    importlib.reload(cs)
    try:
        assert cs.settings.DEVELOPER_MODE is False and cs.settings.PRIVATE_MODE is False
    finally:
        monkeypatch.undo()
        importlib.reload(cs)


def test_app_has_headers_and_hides_errors_and_unauth_is_rejected(monkeypatch):
    from app.main import app
    monkeypatch.setattr(app, "dependency_overrides", {})  # real auth, not the test bypass
    c = TestClient(app, raise_server_exceptions=False)
    r = c.get("/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert c.post("/chat", json={"message": "hi"}).status_code in (401, 403)
    assert c.get("/tasks").status_code in (401, 403)
    big = c.post("/identity/google", content=b"x" * (2 * 1024 * 1024))
    assert big.status_code == 413


def test_cors_rejects_unknown_origin():
    from app.main import app
    c = TestClient(app)
    r = c.options("/chat", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in r.headers


def test_otp_send_throttled_and_hash_peppered():
    m = OTPManager()
    for _ in range(3):
        m.create_challenge("u", "+9779800000000")
    with pytest.raises(OTPRateLimited):
        m.create_challenge("u", "+9779800000000")
    import hashlib
    assert OTPManager._hash("123456") != hashlib.sha256(b"123456").hexdigest()


def test_dev_session_expires(monkeypatch):
    import identity.auth as auth
    monkeypatch.setattr(settings, "DEVELOPER_MODE", True)
    token, _ = auth.create_developer_session("t")
    auth._DEV_SESSIONS[token]["_expires_at"] = 0

    class R:
        headers = {"Authorization": f"Bearer {token}"}
        client = type("C", (), {"host": "127.0.0.1"})()
    with pytest.raises(Exception) as e:
        auth.authenticate_request(R())
    assert "expired" in str(e.value.detail)


def test_google_provider_outage_is_503_not_500(monkeypatch):
    import identity.auth as auth
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "id")

    def boom(*a, **k):
        raise ConnectionError("down")
    monkeypatch.setattr(auth.id_token, "verify_oauth2_token", boom)
    with pytest.raises(Exception) as e:
        auth.verify_google_id_token("tok")
    assert e.value.status_code == 503
