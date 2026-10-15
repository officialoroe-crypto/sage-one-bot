from database.connection import Base, SessionLocal, engine
from database.repository import repository
from app.worker import SageWorker
import app.worker as worker_module


def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_worker_routes_non_research_goal_through_mission_planner(monkeypatch):
    fresh_db()

    db = SessionLocal()
    try:
        task = repository.create_task(
            db=db,
            title='Agent execution test',
            description='Execute this high-level goal',
            priority=1,
            max_retries=3,
        )
        task_id = task.id
    finally:
        db.close()

    worker = SageWorker(
        worker_id='worker-agent-execution',
        lease_seconds=30,
        heartbeat_interval=30,
    )

    claimed = worker.claim()
    assert claimed is not None
    assert claimed['id'] == task_id

    captured = {}

    def fake_plan(**kwargs):
        captured['plan'] = kwargs
        return {'mission': {'id': 'mission-123'}}

    def fake_execute_mission(**kwargs):
        captured['execution'] = kwargs
        return {'success': True, 'status': 'completed'}

    monkeypatch.setattr(worker_module.planner, 'plan', fake_plan)
    monkeypatch.setattr(
        worker_module.parallel_mission_executor,
        'execute_mission',
        fake_execute_mission,
    )

    result = worker.execute_task(claimed)

    assert result['success'] is True
    assert result['mission_id'] == 'mission-123'
    assert captured['plan']['goal'] == claimed['description']
    assert captured['plan']['session_id'] == claimed.get('session_id')
    assert captured['plan']['priority'] == claimed.get('priority', 3)
    assert captured['execution']['mission_id'] == 'mission-123'
    assert captured['execution']['max_steps'] == 20


def test_worker_does_not_claim_mission_child_tasks():
    fresh_db()

    db = SessionLocal()
    try:
        child = repository.create_task(
            db=db,
            title='Mission child',
            description='Owned by mission',
            priority=1,
            max_retries=3,
        )
        child.mission_id = 'mission-child-1'
        db.commit()

        root = repository.create_task(
            db=db,
            title='Root task',
            description='Global durable goal',
            priority=2,
            max_retries=3,
        )
        root_id = root.id
        child_id = child.id
    finally:
        db.close()

    worker = SageWorker(
        worker_id='worker-root-only',
        lease_seconds=30,
        heartbeat_interval=30,
    )

    claimed = worker.claim()
    assert claimed is not None
    assert claimed['id'] == root_id
    assert claimed['mission_id'] is None

    db = SessionLocal()
    try:
        child_after = repository.get_task(db, child_id)
        assert child_after is not None
        assert child_after.status == 'pending'
        assert child_after.worker_id is None
    finally:
        db.close()
