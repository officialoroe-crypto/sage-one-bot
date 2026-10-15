import time

from identity.otp import OTPManager


def test_otp_challenge_is_bound_to_owner_and_expires():
    manager = OTPManager(ttl_seconds=60, max_attempts=2)
    challenge = manager.create_challenge("google:user-1", "+9779800000000")

    assert challenge.owner_key == "google:user-1"
    assert challenge.phone == "+9779800000000"
    assert manager.challenge_phone("google:user-2", challenge.challenge_id) is None
    assert manager.verify("google:user-2", challenge.challenge_id, "000000") is False
    assert manager.challenge_phone("google:user-1", challenge.challenge_id) == "+9779800000000"


def test_otp_wrong_codes_are_limited():
    manager = OTPManager(ttl_seconds=60, max_attempts=2)
    challenge = manager.create_challenge("google:user-1", "+9779800000000")

    assert manager.verify("google:user-1", challenge.challenge_id, "000000") is False
    assert manager.verify("google:user-1", challenge.challenge_id, "111111") is False
    assert manager.verify("google:user-1", challenge.challenge_id, "222222") is False


def test_otp_expiry_rejects_challenge():
    manager = OTPManager(ttl_seconds=1, max_attempts=2)
    challenge = manager.create_challenge("google:user-1", "+9779800000000")
    manager._challenges[challenge.challenge_id] = challenge.__class__(
        challenge_id=challenge.challenge_id,
        owner_key=challenge.owner_key,
        phone=challenge.phone,
        code_hash=challenge.code_hash,
        expires_at=time.time() - 1,
        attempts_remaining=challenge.attempts_remaining,
    )

    assert manager.challenge_phone("google:user-1", challenge.challenge_id) is None
    assert manager.verify("google:user-1", challenge.challenge_id, "000000") is False

def test_production_google_auth_requires_configured_owner(monkeypatch):
    from identity.auth import verify_google_id_token
    from config.settings import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setattr(settings, "OWNER_AUTH_SUBJECT", None)

    monkeypatch.setattr(
        "identity.auth.id_token.verify_oauth2_token",
        lambda *args, **kwargs: {
            "sub": "google-user",
            "iss": "accounts.google.com",
            "email": "owner@example.com",
            "email_verified": True,
        },
    )

    import pytest
    with pytest.raises(Exception, match="owner identity"):
        verify_google_id_token("test-token")


def test_production_google_auth_rejects_non_owner(monkeypatch):
    from identity.auth import verify_google_id_token
    from config.settings import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setattr(settings, "OWNER_AUTH_SUBJECT", "configured-owner")

    monkeypatch.setattr(
        "identity.auth.id_token.verify_oauth2_token",
        lambda *args, **kwargs: {
            "sub": "different-user",
            "iss": "accounts.google.com",
            "email": "other@example.com",
            "email_verified": True,
        },
    )

    import pytest
    with pytest.raises(Exception, match="restricted to its configured owner"):
        verify_google_id_token("test-token")


def test_production_google_auth_accepts_configured_owner(monkeypatch):
    from identity.auth import verify_google_id_token
    from config.settings import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setattr(settings, "OWNER_AUTH_SUBJECT", "configured-owner")

    monkeypatch.setattr(
        "identity.auth.id_token.verify_oauth2_token",
        lambda *args, **kwargs: {
            "sub": "configured-owner",
            "iss": "accounts.google.com",
            "email": "owner@example.com",
            "email_verified": True,
        },
    )

    claims = verify_google_id_token("test-token")
    assert claims["auth_subject"] == "configured-owner"
    assert claims["owner_mode"] is True
