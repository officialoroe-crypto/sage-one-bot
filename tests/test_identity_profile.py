from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from identity import profile
from identity.onboarding import capability_catalog, validate_capabilities


def test_onboarding_capability_catalog_is_multi_select():
    catalog = capability_catalog()

    assert catalog["version"] == 1
    assert catalog["multi_select"] is True
    assert len(catalog["capabilities"]) >= 5
    assert len({item["id"] for item in catalog["capabilities"]}) == len(catalog["capabilities"])


def test_capabilities_are_validated_and_normalized():
    values = validate_capabilities(["research", "learning", "research"])

    assert values == ["learning", "research"]

    try:
        validate_capabilities(["not-a-real-capability"])
    except ValueError as exc:
        assert "Unknown onboarding capabilities" in str(exc)
    else:
        raise AssertionError("Unknown capability should be rejected")


def test_profile_round_trip_and_phone_verification(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'identity.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    monkeypatch.setattr(profile, "SessionLocal", session_factory)

    created = profile.upsert_profile(
        auth_provider="google",
        auth_subject="google-subject-1",
        email="user@example.com",
        name="Test User",
        phone="+9779800000000",
        address="Kathmandu",
        age=25,
        basic_info={"language": "English"},
        help_intent="Learn and earn",
        capabilities=["research", "learning", "research"],
        memory_consent=True,
    )

    assert created["auth_provider"] == "google"
    assert created["name"] == "Test User"
    assert created["phone_verified"] is False
    assert created["capabilities"] == ["learning", "research"]
    assert created["memory_consent"] is True

    verified = profile.mark_phone_verified("google", "google-subject-1")

    assert verified["phone_verified"] is True
    assert verified["phone_verified_at"] is not None

    loaded = profile.get_profile("google", "google-subject-1")

    assert loaded is not None
    assert loaded["email"] == "user@example.com"
    assert loaded["basic_info"] == {"language": "English"}
    assert loaded["help_intent"] == "Learn and earn"
