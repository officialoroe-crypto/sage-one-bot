import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.connection import Base
from database.models import Task
from economy.models import (
    EvolutionProfile,
    PremiumSparkTransaction,
    SparkLedgerEntry,
    SparkWallet,
)
from economy.service import grant_sparks, premium_transaction, reserve_premium_work, snapshot
from app import worker as worker_module
from app.worker import SageWorker


@pytest.fixture
def premium_db(monkeypatch):
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
    monkeypatch.setattr(worker_module, "SessionLocal", session_factory)
    owner_key = "developer:premium-worker-test"
    with session_factory() as db:
        grant_sparks(db, owner_key, 100, "test seed", reference="seed")
    yield session_factory, owner_key
    engine.dispose()


def _task(owner_key, task_id="premium-task-1", status="pending"):
    return {
        "id": task_id,
        "title": "Premium test",
        "description": "Run premium test work",
        "status": status,
        "owner_key": owner_key,
        "premium_work_key": "research_deep",
        "retries": 0,
        "session_id": None,
        "priority": 3,
        "agent": "general",
    }


def _wallet(session_factory, owner_key):
    with session_factory() as db:
        return snapshot(db, owner_key)["spark"]


def test_premium_worker_success_reserves_and_settles_once(premium_db, monkeypatch):
    session_factory, owner_key = premium_db
    task = _task(owner_key)
    worker = SageWorker()
    monkeypatch.setattr(worker, "reconcile_premium_transactions", lambda: None)
    monkeypatch.setattr(worker, "recover_expired_tasks", lambda: None)
    monkeypatch.setattr(worker, "claim", lambda: task)
    monkeypatch.setattr(worker, "execute_task", lambda _task: {"success": True, "result": "ok"})
    monkeypatch.setattr(
        worker_module.tasks,
        "complete_claim",
        lambda **_kwargs: {**task, "status": "completed"},
    )
    monkeypatch.setattr(worker_module, "create_task_notification", lambda *_args, **_kwargs: None)

    result = worker.run_once()

    assert result["success"] is True
    assert _wallet(session_factory, owner_key)["balance"] == 75
    with session_factory() as db:
        transaction = premium_transaction(db, owner_key, "task:premium-task-1")
        assert transaction.status == "settled"
        assert transaction.amount == 25


def test_retry_reuses_reservation_then_settles_without_second_debit(premium_db, monkeypatch):
    session_factory, owner_key = premium_db
    task = _task(owner_key)
    worker = SageWorker()
    attempts = {"count": 0}
    monkeypatch.setattr(worker, "reconcile_premium_transactions", lambda: None)
    monkeypatch.setattr(worker, "recover_expired_tasks", lambda: None)
    monkeypatch.setattr(worker, "claim", lambda: task)

    def execute(_task):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("temporary provider failure")
        return {"success": True, "result": "recovered"}

    monkeypatch.setattr(worker, "execute_task", execute)
    monkeypatch.setattr(
        worker_module.tasks,
        "fail_claim",
        lambda **_kwargs: {**task, "status": "pending", "retries": 1},
    )
    monkeypatch.setattr(
        worker_module.tasks,
        "complete_claim",
        lambda **_kwargs: {**task, "status": "completed"},
    )
    monkeypatch.setattr(worker_module, "create_task_notification", lambda *_args, **_kwargs: None)

    first = worker.run_once()
    assert first["success"] is False
    assert _wallet(session_factory, owner_key)["balance"] == 75
    with session_factory() as db:
        assert premium_transaction(db, owner_key, "task:premium-task-1").status == "reserved"

    second = worker.run_once()
    assert second["success"] is True
    assert _wallet(session_factory, owner_key)["balance"] == 75
    with session_factory() as db:
        transaction = premium_transaction(db, owner_key, "task:premium-task-1")
        assert transaction.status == "settled"
        debits = [
            row for row in snapshot(db, owner_key)["ledger"]
            if row["reference"] == "premium:task:premium-task-1"
        ]
        assert len(debits) == 1


def test_terminal_worker_failure_refunds_reserved_sparks(premium_db, monkeypatch):
    session_factory, owner_key = premium_db
    task = _task(owner_key)
    worker = SageWorker()
    monkeypatch.setattr(worker, "reconcile_premium_transactions", lambda: None)
    monkeypatch.setattr(worker, "recover_expired_tasks", lambda: None)
    monkeypatch.setattr(worker, "claim", lambda: task)
    monkeypatch.setattr(
        worker,
        "execute_task",
        lambda _task: (_ for _ in ()).throw(RuntimeError("terminal failure")),
    )
    monkeypatch.setattr(
        worker_module.tasks,
        "fail_claim",
        lambda **_kwargs: {**task, "status": "failed", "error": "terminal failure"},
    )
    monkeypatch.setattr(worker_module, "create_task_notification", lambda *_args, **_kwargs: None)

    result = worker.run_once()

    assert result["success"] is False
    assert _wallet(session_factory, owner_key)["balance"] == 100
    with session_factory() as db:
        transaction = premium_transaction(db, owner_key, "task:premium-task-1")
        assert transaction.status == "refunded"


@pytest.mark.parametrize(
    ("terminal_status", "expected_transaction_status", "expected_balance"),
    [
        ("completed", "settled", 75),
        ("failed", "refunded", 100),
        ("cancelled", "refunded", 100),
    ],
)
def test_reconciliation_repairs_terminal_task_spark_state(
    premium_db, terminal_status, expected_transaction_status, expected_balance
):
    session_factory, owner_key = premium_db
    task_id = f"reconcile-{terminal_status}"
    with session_factory() as db:
        db.add(
            Task(
                id=task_id,
                title="Reconciliation test",
                description="Terminal premium work",
                status=terminal_status,
                owner_key=owner_key,
                premium_work_key="research_deep",
            )
        )
        reserve_premium_work(db, owner_key, f"task:{task_id}", "research_deep")

    worker = SageWorker()
    worker.reconcile_premium_transactions()
    worker.reconcile_premium_transactions()  # Replays must be harmless.

    with session_factory() as db:
        transaction = premium_transaction(db, owner_key, f"task:{task_id}")
        assert transaction.status == expected_transaction_status
    assert _wallet(session_factory, owner_key)["balance"] == expected_balance


def test_task_migration_adds_premium_columns_and_is_repeatable(monkeypatch, tmp_path):
    from database import migrate as migration_module

    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE tasks (id VARCHAR PRIMARY KEY)"))
    monkeypatch.setattr(migration_module, "engine", engine)

    migration_module.migrate()
    migration_module.migrate()

    columns = {column["name"] for column in inspect(engine).get_columns("tasks")}
    assert {"owner_key", "premium_work_key"}.issubset(columns)
    engine.dispose()
