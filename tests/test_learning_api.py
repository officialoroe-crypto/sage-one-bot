from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import _require_api_access, app
from database.connection import Base, get_db
from identity.auth import authenticate_request
from learning import api as learning_api
from learning.models import LessonProgress


@pytest.fixture
def learning_client(tmp_path, monkeypatch) -> Iterator[tuple[TestClient, dict[str, str]]]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'learning.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine, tables=[LessonProgress.__table__])
    testing_session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    identity = {
        "auth_provider": "test",
        "auth_subject": "learner-one",
        "name": "Learner One",
        "email": "learner@example.test",
    }

    def override_auth() -> dict[str, str]:
        return dict(identity)

    def override_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setitem(app.dependency_overrides, _require_api_access, lambda: None)
    monkeypatch.setitem(app.dependency_overrides, authenticate_request, override_auth)
    monkeypatch.setitem(app.dependency_overrides, get_db, override_db)
    monkeypatch.setattr(learning_api, "_profile_id", lambda claims: str(claims["auth_subject"]))

    client = TestClient(app)
    try:
        yield client, identity
    finally:
        client.close()
        engine.dispose()


def test_learning_catalog_and_completion_are_persisted_and_idempotent(learning_client):
    client, _identity = learning_client

    response = client.get("/learning/paths")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert [path["id"] for path in paths] == [
        "digital-foundations",
        "freelancing-starter",
        "ai-productivity",
    ]
    assert all(path["completed_lessons"] == 0 for path in paths)
    lesson_id = "digital-files-and-documents"

    completed = client.post(f"/learning/lessons/{lesson_id}/complete")
    assert completed.status_code == 200
    assert completed.json()["success"] is True
    assert completed.json()["lesson"]["is_completed"] is True

    # Repeating the same completion is a success, not duplicate progress.
    repeated = client.post(f"/learning/lessons/{lesson_id}/complete")
    assert repeated.status_code == 200

    refreshed = client.get("/learning/paths")
    assert refreshed.status_code == 200
    digital = next(path for path in refreshed.json()["paths"] if path["id"] == "digital-foundations")
    assert digital["completed_lessons"] == 1
    assert digital["total_lessons"] == 3
    assert digital["progress_ratio"] == pytest.approx(1 / 3)
    found = next(lesson for lesson in digital["lessons"] if lesson["id"] == lesson_id)
    assert found["is_completed"] is True
    assert found["completed_at"]


def test_learning_progress_is_private_to_each_authenticated_profile(learning_client):
    client, identity = learning_client
    lesson_id = "freelance-choose-a-service"

    assert client.post(f"/learning/lessons/{lesson_id}/complete").status_code == 200
    identity.update(auth_subject="learner-two", name="Learner Two")

    paths = client.get("/learning/paths").json()["paths"]
    freelancing = next(path for path in paths if path["id"] == "freelancing-starter")
    assert freelancing["completed_lessons"] == 0
    assert all(not lesson["is_completed"] for lesson in freelancing["lessons"])


def test_learning_rejects_unknown_lesson_id(learning_client):
    client, _identity = learning_client
    response = client.post("/learning/lessons/not-a-real-lesson/complete")
    assert response.status_code == 404
    assert response.json()["detail"] == "Learning lesson not found."
