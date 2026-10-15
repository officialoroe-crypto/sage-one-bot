from database.connection import Base, SessionLocal, engine
from database.repository import repository
from identity.profile import UserProfile
from workflows.repository import repository as workflow_repository
from app.main import CommandRequest, command
from app.worker import SageWorker


def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_command_creates_owned_durable_task_with_project_context():
    fresh_db()
    claims = {
        "auth_provider": "developer",
        "auth_subject": "owner-test",
        "owner_mode": True,
        "developer_mode": True,
    }

    profile = None
    with SessionLocal() as db:
        profile = UserProfile(
            id="profile-owner-test",
            auth_provider="developer",
            auth_subject="owner-test",
            memory_consent=1,
            onboarding_completed=1,
        )
        db.add(profile)
        db.commit()
        profile_id = profile.id

        workspace = workflow_repository.create_workspace(
            db,
            profile_id,
            "SAGE ONE",
            "sage-one",
            "personal",
            {},
        )
        project = workflow_repository.create_project(
            db,
            workspace,
            "Execution Loop",
            "general",
            "Core execution-loop validation project.",
            {},
        )
        project_id = project.id

    response = command(
        CommandRequest(
            message="Build the execution loop",
            project_id=project_id,
            priority=2,
        ),
        claims,
    )

    assert response["success"] is True
    task = response["task"]
    assert task["project_id"] == project_id
    assert task["status"] == "pending"

    with SessionLocal() as db:
        stored = repository.get_task(db, task["id"])
        assert stored is not None
        assert stored.profile_id == profile_id
        assert stored.project_id == project_id


def test_completed_task_indexes_project_result_and_learns_with_consent():
    fresh_db()

    with SessionLocal() as db:
        profile = UserProfile(
            id="profile-memory-test",
            auth_provider="developer",
            auth_subject="memory-owner",
            memory_consent=1,
            onboarding_completed=1,
        )
        db.add(profile)
        db.commit()
        profile_id = profile.id

        workspace = workflow_repository.create_workspace(
            db,
            profile_id,
            "SAGE ONE",
            "sage-one-memory",
            "personal",
            {},
        )
        project = workflow_repository.create_project(
            db,
            workspace,
            "Memory Loop",
            "general",
            None,
            {},
        )
        project_id = project.id
        task = repository.create_task(
            db=db,
            title="Persistent result",
            description="Produce a durable project result",
            profile_id=profile_id,
            project_id=project_id,
        )
        task_payload = {
            "id": task.id,
            "title": task.title,
            "session_id": task.session_id,
            "profile_id": task.profile_id,
            "project_id": task.project_id,
        }

    worker = SageWorker(worker_id="outcome-test")
    worker._persist_task_outcome(task_payload, {"success": True, "answer": "done"})

    with SessionLocal() as db:
        assets = workflow_repository.list_assets(db, profile_id, project_id)
        assert len(assets) == 1
        assert assets[0].asset_type == "text"
        assert assets[0].status == "completed"

    memories = __import__("identity.memory", fromlist=["list_memory"]).list_memory(profile_id)
    assert any("Persistent result" in item["content"] for item in memories)


def test_task_migration_contains_project_context_columns():
    from database import migrate as migration_module
    from sqlalchemy import inspect

    fresh_db()
    migration_module.migrate()

    columns = {item["name"] for item in inspect(engine).get_columns("tasks")}
    assert "profile_id" in columns
    assert "project_id" in columns


def test_sessions_are_owner_scoped_and_command_rejects_foreign_session():
    fresh_db()
    owner_a = {
        "auth_provider": "developer",
        "auth_subject": "owner-a",
        "owner_mode": True,
        "developer_mode": True,
    }
    owner_b = {
        "auth_provider": "developer",
        "auth_subject": "owner-b",
        "owner_mode": True,
        "developer_mode": True,
    }

    from app.main import get_session, command
    with SessionLocal() as db:
        session_id = repository.create_session(
            db,
            profile_id="profile-a",
            owner_key="developer:owner-a",
        )

    created = get_session(session_id, owner_a)
    assert created["success"] is True
    assert created["session"]["owner_key"] == "developer:owner-a"

    try:
        get_session(session_id, owner_b)
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 404
    else:
        raise AssertionError("foreign owner unexpectedly accessed a session")

    try:
        command(
            CommandRequest(message="should be rejected", session_id=session_id),
            owner_b,
        )
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 404
    else:
        raise AssertionError("foreign owner unexpectedly queued into another session")


def test_session_migration_contains_owner_context_columns():
    from database import migrate as migration_module
    from sqlalchemy import inspect

    fresh_db()
    migration_module.migrate()

    columns = {item["name"] for item in inspect(engine).get_columns("sessions")}
    assert "profile_id" in columns
    assert "owner_key" in columns


def test_tasks_are_owner_scoped_for_reads_and_cancellation():
    fresh_db()
    with SessionLocal() as db:
        task_a = repository.create_task(
            db=db,
            title="Owner A",
            description="private task",
            owner_key="developer:owner-a",
        )
        task_a_id = task_a.id
    with SessionLocal() as db:
        task_b = repository.create_task(
            db=db,
            title="Owner B",
            description="private task",
            owner_key="developer:owner-b",
        )
        task_b_id = task_b.id

    from tasks.engine import tasks
    assert tasks.get(task_a_id, owner_key="developer:owner-a") is not None
    assert tasks.get(task_a_id, owner_key="developer:owner-b") is None
    assert len(tasks.list(owner_key="developer:owner-a")) == 1
    assert tasks.cancel(task_a_id, owner_key="developer:owner-b") is None
    assert tasks.cancel(task_a_id, owner_key="developer:owner-a")["status"] == "cancelled"
    assert tasks.get(task_b_id, owner_key="developer:owner-b") is not None


def test_legacy_memory_is_owner_scoped():
    fresh_db()
    claims_a = {
        "auth_provider": "developer",
        "auth_subject": "memory-owner-a",
        "owner_mode": True,
        "developer_mode": True,
    }
    claims_b = {
        "auth_provider": "developer",
        "auth_subject": "memory-owner-b",
        "owner_mode": True,
        "developer_mode": True,
    }

    from app.main import add_memory, get_memory
    created = add_memory(
        __import__("app.main", fromlist=["MemoryRequest"]).MemoryRequest(
            content="private owner A memory",
            memory_type="fact",
            importance=1,
            confidence=1.0,
            source="test",
        ),
        claims_a,
    )
    assert created["success"] is True

    visible_a = get_memory(claims_a)
    visible_b = get_memory(claims_b)
    assert any(item["content"] == "private owner A memory" for item in visible_a["memories"])
    assert all(item["content"] != "private owner A memory" for item in visible_b["memories"])


def test_memory_migration_contains_owner_context_columns():
    from database import migrate as migration_module
    from sqlalchemy import inspect

    fresh_db()
    migration_module.migrate()

    columns = {item["name"] for item in inspect(engine).get_columns("memories")}
    assert "owner_key" in columns
    assert "profile_id" in columns
