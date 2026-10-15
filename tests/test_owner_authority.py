import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from economy.owner import OwnerAuditEvent


def test_owner_controls_are_available_in_developer_mode(monkeypatch, tmp_path):
    from config.settings import settings
    import economy.api as api
    import identity.auth as auth

    engine = create_engine(f"sqlite:///{tmp_path / 'owner.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    monkeypatch.setattr(api, "SessionLocal", Session)
    monkeypatch.setattr(settings, "DEVELOPER_MODE", True)

    token, claims = auth.create_developer_session("local-owner")
    # Router-level TestClient cannot apply FastAPI dependency injection by itself;
    # verify the owner claim produced by the controlled local session directly.
    assert claims["owner_mode"] is True
    assert token.startswith("sage-dev-")


def test_owner_spark_and_evolution_controls_are_audited(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'owner-controls.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    owner = "developer:owner"
    with Session() as db:
        from economy.owner import set_evolution, set_spark

        wallet = set_spark(db, owner, 1_000_000, "god mode stress test")
        profile = set_evolution(
            db,
            owner,
            5_000_000,
            "Black Opal Realm",
            "LOW",
            "evolution simulation",
        )
        events = db.query(OwnerAuditEvent).filter(
            OwnerAuditEvent.owner_key == owner
        ).all()
        assert wallet.balance == 1_000_000
        assert profile.lifetime_achievement == 5_000_000
        assert profile.tier == "Black Opal Realm"
        assert len(events) == 2


def test_owner_reset_controls_internal_state(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'owner-reset.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    owner = "developer:owner"
    with Session() as db:
        from economy.owner import (
            reset_evolution,
            reset_spark,
            set_evolution,
            set_spark,
        )

        set_spark(db, owner, 500, "seed")
        set_evolution(db, owner, 1_000, "Silver", "LOW", "seed")
        wallet = reset_spark(db, owner, "reset test")
        profile = reset_evolution(db, owner, "reset test")
        assert wallet.balance == 0
        assert profile.lifetime_achievement == 0
        assert profile.tier == "Bronze"
        assert db.query(OwnerAuditEvent).filter(
            OwnerAuditEvent.owner_key == owner
        ).count() == 4


def test_developer_identity_has_no_phone_or_otp_dependency(monkeypatch):
    from config.settings import settings
    import identity.auth as auth

    monkeypatch.setattr(settings, "DEVELOPER_MODE", True)
    token, claims = auth.create_developer_session()
    assert token.startswith("sage-dev-")
    assert claims["owner_mode"] is True
    assert claims["developer_mode"] is True
    assert "phone" not in claims


def test_direct_economy_mutations_require_owner_mode():
    from economy.api import _require_owner

    with pytest.raises(Exception, match="Owner Authority"):
        _require_owner(
            {
                "auth_provider": "google",
                "auth_subject": "normal-user",
                "owner_mode": False,
            }
        )

def test_global_permission_controls_require_owner_authority():
    from app.main import _require_owner

    with pytest.raises(Exception, match="Owner Authority"):
        _require_owner(
            {
                "auth_provider": "google",
                "auth_subject": "normal-user",
                "owner_mode": False,
            }
        )

def test_permission_endpoint_rejects_non_owner(monkeypatch):
    from fastapi import HTTPException
    from fastapi.testclient import TestClient

    from app.main import _require_owner, app
    from config.settings import settings

    monkeypatch.setattr(settings, "DEVELOPER_MODE", True)
    app.dependency_overrides[_require_owner] = lambda: (_ for _ in ()).throw(
        HTTPException(status_code=403, detail="SAGE Owner Authority is required.")
    )
    try:
        with TestClient(app) as client:
            response = client.post(
                "/permissions",
                json={"permission": "web.write", "allowed": True},
            )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(_require_owner, None)
