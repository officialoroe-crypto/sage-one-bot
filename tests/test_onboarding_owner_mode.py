from identity.api import _requires_phone_verification


def test_private_owner_onboarding_does_not_require_phone():
    claims = {"owner_mode": True}
    profile = {"phone_verified": False}
    assert _requires_phone_verification(claims, profile) is False


def test_external_identity_onboarding_requires_verified_phone():
    claims = {"owner_mode": False}
    assert _requires_phone_verification(claims, {"phone_verified": False}) is True
    assert _requires_phone_verification(claims, {"phone_verified": True}) is False
