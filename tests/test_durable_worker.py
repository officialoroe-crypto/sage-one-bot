from datetime import datetime, timedelta, timezone

from database.connection import Base, SessionLocal, engine
from database.repository import repository


def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def make_task(max_retries=3):
    db = SessionLocal()
    try:
        task = repository.create_task(
            db=db,
            title='Worker test',
            description='Worker test task',
            priority=1,
            max_retries=max_retries,
        )
        return task.id
    finally:
        db.close()


def test_single_worker_can_claim_task():
    fresh_db()
    task_id = make_task()

    db = SessionLocal()
    try:
        task = repository.claim_next_task(db, 'worker-a', lease_seconds=120)
        assert task is not None
        assert task.id == task_id
        assert task.status == 'running'
        assert task.worker_id == 'worker-a'
        assert task.lease_expires_at is not None
        assert task.heartbeat_at is not None
    finally:
        db.close()


def test_second_worker_cannot_claim_same_task():
    fresh_db()
    task_id = make_task()

    db = SessionLocal()
    try:
        first = repository.claim_next_task(db, 'worker-a', lease_seconds=120)
        second = repository.claim_next_task(db, 'worker-b', lease_seconds=120)

        assert first is not None
        assert first.id == task_id
        assert second is None
    finally:
        db.close()


def test_heartbeat_requires_owner_and_extends_lease():
    fresh_db()
    task_id = make_task()

    db = SessionLocal()
    try:
        claimed = repository.claim_next_task(db, 'worker-a', lease_seconds=30)
        original_lease = claimed.lease_expires_at

        wrong = repository.heartbeat_task(
            db,
            task_id,
            'worker-b',
            lease_seconds=120,
        )
        assert wrong is None

        updated = repository.heartbeat_task(
            db,
            task_id,
            'worker-a',
            lease_seconds=120,
        )
        assert updated is not None
        assert updated.worker_id == 'worker-a'
        assert updated.lease_expires_at > original_lease
        assert updated.heartbeat_at is not None
    finally:
        db.close()


def test_completion_requires_owner():
    fresh_db()
    task_id = make_task()

    db = SessionLocal()
    try:
        repository.claim_next_task(db, 'worker-a', lease_seconds=120)

        wrong = repository.complete_task_claim(
            db,
            task_id,
            'worker-b',
            'bad completion',
        )
        assert wrong is None

        correct = repository.complete_task_claim(
            db,
            task_id,
            'worker-a',
            'success',
        )
        assert correct is not None
        assert correct.status == 'completed'
        assert correct.result == 'success'
        assert correct.worker_id is None
        assert correct.lease_expires_at is None
    finally:
        db.close()


def test_failure_schedules_retry():
    fresh_db()
    task_id = make_task(max_retries=3)

    db = SessionLocal()
    try:
        repository.claim_next_task(db, 'worker-a', lease_seconds=120)

        failed = repository.fail_task_claim(
            db,
            task_id,
            'worker-a',
            'temporary failure',
            retry_delay_seconds=60,
        )

        assert failed is not None
        assert failed.status == 'pending'
        assert failed.retries == 1
        assert failed.error == 'temporary failure'
        assert failed.worker_id is None
        assert failed.lease_expires_at is None
        assert failed.next_retry_at is not None
        assert repository._normalize_datetime(failed.next_retry_at) > datetime.now(timezone.utc)
    finally:
        db.close()


def test_expired_lease_is_recovered_with_retry_budget():
    fresh_db()
    task_id = make_task(max_retries=2)

    db = SessionLocal()
    try:
        claimed = repository.claim_next_task(db, 'worker-a', lease_seconds=120)
        claimed.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()

        recovered = repository.recover_expired_tasks(db)
        assert recovered == 1

        task = repository.get_task(db, task_id)
        assert task.status == 'pending'
        assert task.retries == 1
        assert task.worker_id is None
        assert task.lease_expires_at is None
        assert task.heartbeat_at is None
        assert task.next_retry_at is not None

        claimed_again = repository.claim_next_task(db, 'worker-b', lease_seconds=120)
        claimed_again.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()

        repository.recover_expired_tasks(db)
        exhausted = repository.get_task(db, task_id)
        assert exhausted.status == 'failed'
        assert exhausted.retries == 2
        assert exhausted.worker_id is None
        assert exhausted.lease_expires_at is None
        assert exhausted.next_retry_at is None
        assert exhausted.completed_at is not None
    finally:
        db.close()
