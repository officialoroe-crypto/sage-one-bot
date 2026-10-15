from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app import worker as worker_module
from app.main import _require_owner, app
from app.worker import SageWorker
from database.connection import Base
from database.models import Task
from tasks import engine as task_engine
from economy.models import (
    EvolutionProfile,
    PremiumSparkTransaction,
    SparkLedgerEntry,
    SparkWallet,
)
from economy.service import grant_sparks, premium_transaction, snapshot


client = TestClient(app)


def test_premium_task_api_to_worker_settles_spark_end_to_end(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Task.__table__,
            SparkWallet.__table__,
            SparkLedgerEntry.__table__,
            EvolutionProfile.__table__,
            PremiumSparkTransaction.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(task_engine, "SessionLocal", session_factory)
    monkeypatch.setattr(worker_module, "SessionLocal", session_factory)

    claims = {
        "auth_provider": "developer",
        "auth_subject": "dev:e2e-owner",
        "owner_mode": True,
    }
    monkeypatch.setitem(app.dependency_overrides, _require_owner, lambda: claims)
    monkeypatch.setattr(
        worker_module,
        "create_task_notification",
        lambda *_args, **_kwargs: None,
    )

    owner_key = "developer:dev:e2e-owner"
    with session_factory() as db:
        grant_sparks(db, owner_key, 100, "test seed", reference="e2e-seed")

    try:
        response = client.post(
            "/tasks/premium",
            json={
                "title": "End-to-end premium research",
                "description": "Research the requested topic",
                "work_key": "research_deep",
            },
        )
        assert response.status_code == 200
        assert "owner_key" not in response.json()["task"]
        task_id = response.json()["task"]["id"]

        worker = SageWorker()
        worker_input = {}

        def execute_premium(task):
            worker_input.update(task)
            return {"success": True, "result": "verified test result"}

        monkeypatch.setattr(worker, "execute_task", execute_premium)
        result = worker.run_once()

        assert result["success"] is True
        assert worker_input["owner_key"] == owner_key
        assert result["task"]["id"] == task_id
        assert result["task"]["status"] == "completed"

        task_response = client.get(f"/tasks/{task_id}")
        assert task_response.status_code == 200
        assert task_response.json()["task"]["status"] == "completed"

        with session_factory() as db:
            transaction = premium_transaction(db, owner_key, f"task:{task_id}")
            wallet = snapshot(db, owner_key)["spark"]
            assert transaction is not None
            assert transaction.status == "settled"
            assert transaction.amount == 25
            assert wallet["balance"] == 75
            assert wallet["lifetime_spent"] == 25
    finally:
        app.dependency_overrides.pop(_require_owner, None)
        engine.dispose()
