from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import _require_api_access, app
from database.connection import Base, get_db
from identity.auth import authenticate_request
from opportunities import api as opportunities_api
from opportunities.models import JobApplication, JobPosting, MarketplaceInquiry, MarketplaceListing


@pytest.fixture
def opportunity_client(tmp_path, monkeypatch) -> Iterator[tuple[TestClient, dict[str, str]]]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'opportunities.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[
            JobPosting.__table__,
            JobApplication.__table__,
            MarketplaceListing.__table__,
            MarketplaceInquiry.__table__,
        ],
    )
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    identity = {
        "auth_provider": "test",
        "auth_subject": "employer",
        "name": "Kathmandu Employer",
        "email": "employer@example.test",
    }

    def override_auth() -> dict[str, str]:
        return dict(identity)

    def override_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setitem(app.dependency_overrides, _require_api_access, lambda: None)
    monkeypatch.setitem(app.dependency_overrides, authenticate_request, override_auth)
    monkeypatch.setitem(app.dependency_overrides, get_db, override_db)
    monkeypatch.setattr(
        opportunities_api,
        "_profile_identity",
        lambda claims: (
            str(claims["auth_subject"]),
            str(claims.get("name") or "SAGE user"),
        ),
    )
    client = TestClient(app)
    try:
        yield client, identity
    finally:
        client.close()
        engine.dispose()


def test_public_display_name_never_falls_back_to_email(monkeypatch):
    from opportunities import api as opportunities_api

    monkeypatch.setattr(
        opportunities_api,
        "get_or_create_authenticated_profile",
        lambda claims: {"id": "profile-1", "name": None},
    )

    profile_id, display_name = opportunities_api._profile_identity(
        {
            "auth_provider": "google",
            "auth_subject": "subject-1",
            "name": None,
            "email": "private-address@example.test",
        }
    )

    assert profile_id == "profile-1"
    assert display_name == "SAGE user"
    assert "private-address@example.test" not in display_name


def test_job_listing_application_lifecycle_is_identity_scoped(opportunity_client):
    client, identity = opportunity_client

    created = client.post(
        "/jobs",
        json={
            "title": "Junior Flutter Developer",
            "company": "SAGE Demo",
            "description": "Build and test mobile features.",
            "location": "Kathmandu, Nepal",
            "employment_type": "full_time",
            "salary_min_npr": 30000,
            "salary_max_npr": 60000,
        },
    )
    assert created.status_code == 201
    job = created.json()["job"]
    assert job["status"] == "open"
    assert job["salary_min_npr"] == 30000

    assert client.get("/jobs/mine").json()["jobs"][0]["id"] == job["id"]

    identity.update(
        auth_subject="applicant",
        name="Nepali Applicant",
        email="applicant@example.test",
    )
    browse = client.get("/jobs", params={"query": "Flutter", "location": "Kathmandu"})
    assert browse.status_code == 200
    assert [item["id"] for item in browse.json()["jobs"]] == [job["id"]]

    application = client.post(
        f"/jobs/{job['id']}/applications",
        json={"cover_note": "I have Flutter and Dart project experience."},
    )
    assert application.status_code == 201
    assert application.json()["application"]["status"] == "submitted"
    assert application.json()["message"] == "Application submitted."

    duplicate = client.post(
        f"/jobs/{job['id']}/applications",
        json={"cover_note": "Trying to send a second application."},
    )
    assert duplicate.status_code == 409
    assert "already applied" in duplicate.json()["detail"]

    # A different user cannot read the employer's applicant records or close the job.
    assert client.get(f"/jobs/{job['id']}/applications").status_code == 404
    assert client.post(f"/jobs/{job['id']}/close").status_code == 404
    assert len(client.get("/jobs/applications/mine").json()["applications"]) == 1

    identity.update(
        auth_subject="employer",
        name="Kathmandu Employer",
        email="employer@example.test",
    )
    employer_view = client.get(f"/jobs/{job['id']}/applications")
    assert employer_view.status_code == 200
    items = employer_view.json()["applications"]
    assert len(items) == 1
    assert items[0]["applicant_name"] == "Nepali Applicant"
    assert items[0]["cover_note"] == "I have Flutter and Dart project experience."

    closed = client.post(f"/jobs/{job['id']}/close")
    assert closed.status_code == 200
    assert closed.json()["job"]["status"] == "closed"
    assert client.get("/jobs").json()["jobs"] == []


def test_job_validation_and_duplicate_protection(opportunity_client):
    client, identity = opportunity_client
    invalid_salary = client.post(
        "/jobs",
        json={
            "title": "Role",
            "company": "Company",
            "description": "Details",
            "location": "Pokhara",
            "salary_min_npr": 80000,
            "salary_max_npr": 30000,
        },
    )
    assert invalid_salary.status_code == 422

    blank_title = client.post(
        "/jobs",
        json={
            "title": "   ",
            "company": "Company",
            "description": "Details",
            "location": "Pokhara",
        },
    )
    assert blank_title.status_code == 422

    created = client.post(
        "/jobs",
        json={
            "title": "Support assistant",
            "company": "Example",
            "description": "Help customers",
            "location": "Pokhara",
        },
    )
    assert created.status_code == 201
    identity.update(auth_subject="other-employer", name="Other Employer")
    other_user = client.get(f"/jobs/{created.json()['job']['id']}/applications")
    assert other_user.status_code == 404


def test_marketplace_listing_and_inquiry_lifecycle_is_identity_scoped(opportunity_client):
    client, identity = opportunity_client
    created = client.post(
        "/marketplace/listings",
        json={
            "title": "Used Honda scooter",
            "category": "vehicles",
            "description": "Well-maintained scooter; viewing by appointment.",
            "location": "Lalitpur, Nepal",
            "price_npr": 185000,
            "item_condition": "used",
        },
    )
    assert created.status_code == 201
    listing = created.json()["listing"]
    assert listing["price_npr"] == 185000
    assert listing["status"] == "active"

    identity.update(
        auth_subject="buyer",
        name="Local Buyer",
        email="buyer@example.test",
    )
    browse = client.get("/marketplace/listings", params={"category": "vehicles", "location": "Lalitpur"})
    assert browse.status_code == 200
    assert [item["id"] for item in browse.json()["listings"]] == [listing["id"]]

    inquiry = client.post(
        f"/marketplace/listings/{listing['id']}/inquiries",
        json={"message": "Is the scooter available for a viewing this weekend?"},
    )
    assert inquiry.status_code == 201
    assert inquiry.json()["message"] == "Interest sent to the seller."

    duplicate = client.post(
        f"/marketplace/listings/{listing['id']}/inquiries",
        json={"message": "Please contact me."},
    )
    assert duplicate.status_code == 409

    # Buyers cannot read the seller inbox or close another user's listing.
    assert client.get(f"/marketplace/listings/{listing['id']}/inquiries").status_code == 404
    assert client.post(f"/marketplace/listings/{listing['id']}/close").status_code == 404
    buyer_items = client.get("/marketplace/inquiries/mine").json()["inquiries"]
    assert len(buyer_items) == 1
    assert buyer_items[0]["listing"]["title"] == "Used Honda scooter"

    identity.update(
        auth_subject="employer",
        name="Kathmandu Employer",
        email="employer@example.test",
    )
    # The original seller profile id is its auth_subject ('test') in this fixture.
    seller_view = client.get(f"/marketplace/listings/{listing['id']}/inquiries")
    assert seller_view.status_code == 200
    seller_inquiries = seller_view.json()["inquiries"]
    assert len(seller_inquiries) == 1
    assert seller_inquiries[0]["buyer_name"] == "Local Buyer"
    assert "phone" not in seller_inquiries[0]

    closed = client.post(f"/marketplace/listings/{listing['id']}/close")
    assert closed.status_code == 200
    assert closed.json()["listing"]["status"] == "closed"
    assert client.get("/marketplace/listings").json()["listings"] == []


def test_marketplace_rejects_invalid_price_and_self_inquiries(opportunity_client):
    client, identity = opportunity_client
    invalid = client.post(
        "/marketplace/listings",
        json={
            "title": "Phone",
            "category": "electronics",
            "description": "Used phone",
            "location": "Kathmandu",
            "price_npr": 0,
            "item_condition": "used",
        },
    )
    assert invalid.status_code == 422

    created = client.post(
        "/marketplace/listings",
        json={
            "title": "Basic computer course",
            "category": "courses",
            "description": "Weekend beginner course",
            "location": "Kathmandu",
            "price_npr": 2500,
            "item_condition": "service",
        },
    )
    assert created.status_code == 201
    listing_id = created.json()["listing"]["id"]
    self_inquiry = client.post(
        f"/marketplace/listings/{listing_id}/inquiries",
        json={"message": "I am asking about my own listing."},
    )
    assert self_inquiry.status_code == 409

    identity.update(auth_subject="someone-else", name="Another User")
    assert client.get(f"/marketplace/listings/{listing_id}/inquiries").status_code == 404
