from identity import api
from identity.auth import verify_google_id_token
from identity.onboarding import capability_catalog

def test_identity_api_contract_has_onboarding_and_memory_endpoints():
    paths = {(route.path, tuple(sorted(route.methods or []))) for route in api.router.routes}
    assert ("/identity/config", ("GET",)) in paths
    assert ("/identity/dev-login", ("POST",)) in paths
    assert ("/identity/google", ("POST",)) in paths
    assert ("/identity/me", ("GET",)) in paths
    assert ("/identity/onboarding/options", ("GET",)) in paths
    assert ("/identity/onboarding", ("POST",)) in paths
    assert ("/identity/phone/send", ("POST",)) in paths
    assert ("/identity/phone/verify", ("POST",)) in paths
    assert ("/identity/memory", ("GET",)) in paths
    assert ("/identity/memory", ("POST",)) in paths

def test_google_verifier_requires_server_configuration(monkeypatch):
    from config.settings import settings
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", None)
    monkeypatch.setattr(settings, "DEVELOPER_MODE", False)
    try:
        verify_google_id_token("fake-token")
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 503
    else:
        raise AssertionError("Unconfigured Google auth should fail closed")

def test_capability_catalog_matches_api_source():
    response = api.onboarding_options()
    assert response["success"] is True
    assert response["multi_select"] is True
    assert response["version"] == capability_catalog()["version"]

def test_developer_login_is_disabled_by_default(monkeypatch):
    from identity import api
    from config.settings import settings
    from fastapi import HTTPException
    from unittest.mock import Mock
    monkeypatch.setattr(settings, "DEVELOPER_MODE", False)
    request = Mock()
    request.client.host = "127.0.0.1"
    try:
        api.developer_login(request, api.DeveloperLoginRequest(label="local-owner"))
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("Developer login must be disabled by default")


def test_capability_validation_uses_stable_ids():
    from identity.onboarding import validate_capabilities

    assert validate_capabilities(["content", "learning", "content"]) == ["content", "learning"]
    try:
        validate_capabilities(["Content Creation"])
    except ValueError as exc:
        assert "Unknown onboarding capabilities" in str(exc)
    else:
        raise AssertionError("Human-facing capability labels must not be accepted as stored IDs")


def test_private_owner_onboarding_allows_missing_phone():
    request = api.OnboardingRequest(
        name="Owner", address="Private workspace", age=25,
        help_intent="Build SAGE ONE", capabilities=[], memory_consent=False,
    )
    assert request.phone is None


def test_phone_send_request_requires_phone():
    import pydantic
    try:
        api.PhoneRequest.model_validate({})
    except pydantic.ValidationError:
        return
    raise AssertionError("OTP send requests must require a phone number")
