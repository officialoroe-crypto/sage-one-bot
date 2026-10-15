import json
import uuid

from datetime import datetime, timezone

from database.connection import SessionLocal
from events.service import event_store
from config.settings import settings
from economy.achievements import VERIFIED_TASK_ACHIEVEMENT, record_verified_achievement

from database.models import (
    Mission,
    Task,
    VerificationCriterion,
    ExecutionAttempt,
    Artifact,
    RecoveryAttempt,
)



class MissionEngine:

    def __init__(self):
        pass

    # ============================================================
    # TIME
    # ============================================================

    @staticmethod
    def now():
        return datetime.now(timezone.utc)

    # ============================================================
    # CREATE MISSION
    # ============================================================

    def create_mission(
        self,
        goal: str,
        session_id: str | None = None,
        priority: int = 3,
        owner_key: str | None = None,
    ):

        mission_id = str(uuid.uuid4())

        with SessionLocal() as db:

            mission = Mission(
                id=mission_id,
                owner_key=owner_key,
                goal=goal,
                status="planning",
                priority=priority,
                session_id=session_id,
                plan_version=1,
                verification_status="pending",
                created_at=self.now(),
                updated_at=self.now(),
            )

            db.add(mission)
            db.commit()

            db.refresh(mission)

            return self.serialize_mission(
                mission
            )

    # ============================================================
    # GET MISSION
    # ============================================================

    def get_mission(
        self,
        mission_id: str,
        owner_key: str | None = None,
    ):

        with SessionLocal() as db:

            mission = (
                db.query(Mission)
                .filter(
                    Mission.id == mission_id,
                    *([Mission.owner_key == owner_key] if owner_key is not None else []),
                )
                .first()
            )

            if not mission:
                return None

            return self.serialize_mission(
                mission
            )

    # ============================================================
    # CREATE TASK
    # ============================================================

    def create_task(
        self,
        mission_id: str,
        title: str,
        description: str,
        priority: int = 3,
        agent: str = "general",
        depends_on: list[str] | None = None,
        max_retries: int = 3,
    ):

        task_id = str(uuid.uuid4())

        dependency_data = (
            json.dumps(depends_on)
            if depends_on
            else None
        )

        with SessionLocal() as db:

            mission = (
                db.query(Mission)
                .filter(
                    Mission.id == mission_id
                )
                .first()
            )

            if not mission:

                raise ValueError(
                    f"Mission not found: {mission_id}"
                )

            task = Task(
                id=task_id,
                title=title,
                description=description,
                status="pending",
                priority=priority,
                agent=agent,
                session_id=mission.session_id,
                mission_id=mission_id,
                depends_on=dependency_data,
                progress=0,
                retries=0,
                max_retries=max_retries,
                verification_status="pending",
                created_at=self.now(),
                updated_at=self.now(),
            )

            db.add(task)

            mission.updated_at = self.now()

            db.commit()

            db.refresh(task)

            return self.serialize_task(
                task
            )

    # ============================================================
    # GET TASKS
    # ============================================================

    def get_tasks(
        self,
        mission_id: str
    ):

        with SessionLocal() as db:

            tasks = (
                db.query(Task)
                .filter(
                    Task.mission_id == mission_id
                )
                .order_by(
                    Task.priority.asc(),
                    Task.created_at.asc()
                )
                .all()
            )

            return [
                self.serialize_task(task)
                for task in tasks
            ]

    # ============================================================
    # DEPENDENCY RESOLUTION
    # ============================================================

    def dependencies_satisfied(
        self,
        task: Task,
        task_map: dict[str, Task]
    ):

        if not task.depends_on:
            return True

        try:

            dependencies = json.loads(
                task.depends_on
            )

        except Exception:

            return False

        for dependency_id in dependencies:

            dependency = task_map.get(
                dependency_id
            )

            if not dependency:
                return False

            if dependency.status != "completed":
                return False

            if dependency.verification_status != "verified":
                return False

        return True

    # ============================================================
    # FIND NEXT READY TASK
    # ============================================================

    def get_ready_tasks(
        self,
        mission_id: str
    ):

        with SessionLocal() as db:

            tasks = (
                db.query(Task)
                .filter(
                    Task.mission_id == mission_id
                )
                .order_by(
                    Task.priority.asc(),
                    Task.created_at.asc()
                )
                .all()
            )

            task_map = {
                task.id: task
                for task in tasks
            }

            ready = []

            for task in tasks:

                if task.status != "pending":
                    continue

                if self.dependencies_satisfied(
                    task,
                    task_map
                ):

                    ready.append(
                        self.serialize_task(
                            task
                        )
                    )

            return ready

    # ============================================================
    # START TASK
    # ============================================================

    def start_task(
        self,
        task_id: str
    ):

        with SessionLocal() as db:

            task = (
                db.query(Task)
                .filter(
                    Task.id == task_id
                )
                .first()
            )

            if not task:
                raise ValueError(
                    f"Task not found: {task_id}"
                )

            if task.status != "pending":

                raise ValueError(
                    f"Task cannot start from status: "
                    f"{task.status}"
                )

            now = self.now()
            task.status = "running"
            task.started_at = now
            task.updated_at = now
            task.progress = 0

            # Task state and its execution attempt are one state transition.
            # Commit them together so a failure cannot leave a running task
            # without a durable attempt record.
            attempt = ExecutionAttempt(
                id=str(uuid.uuid4()),
                mission_id=task.mission_id,
                task_id=task.id,
                attempt_number=task.retries + 1,
                status="running",
                agent=task.agent,
                created_at=now,
            )

            db.add(attempt)
            db.commit()

            db.refresh(task)
            db.refresh(attempt)

            event_store.emit(
                event_type="TaskStarted",
                task_id=task.id,
                mission_id=task.mission_id,
                session_id=task.session_id,
                status=task.status,
                payload={"attempt_id": attempt.id, "title": task.title},
            )

            return {
                "task": self.serialize_task(task),
                "attempt_id": attempt.id,
            }

    # ============================================================
    # COMPLETE TASK
    # ============================================================

    def complete_task(
        self,
        task_id: str,
        result=None
    ):

        with SessionLocal() as db:

            task = (
                db.query(Task)
                .filter(
                    Task.id == task_id
                )
                .first()
            )

            if not task:
                raise ValueError(
                    f"Task not found: {task_id}"
                )

            task.status = "completed"
            task.progress = 100
            task.result = json.dumps(
                result,
                default=str
            )
            task.verification_status = "pending"
            task.completed_at = self.now()
            task.updated_at = self.now()

            attempts = (
                db.query(ExecutionAttempt)
                .filter(
                    ExecutionAttempt.task_id
                    == task_id
                )
                .order_by(
                    ExecutionAttempt.created_at.desc()
                )
                .all()
            )

            if attempts:

                attempt = attempts[0]

                attempt.status = "completed"
                attempt.result = json.dumps(
                    result,
                    default=str
                )
                attempt.completed_at = self.now()

            db.commit()

            db.refresh(task)

            event_store.emit(
                event_type="TaskCompleted",
                task_id=task.id,
                mission_id=task.mission_id,
                session_id=task.session_id,
                status=task.status,
                payload={"result": result},
            )

            return self.serialize_task(
                task
            )

    # ============================================================
    # FAIL TASK
    # ============================================================

    def fail_task(
        self,
        task_id: str,
        error: str
    ):

        with SessionLocal() as db:

            task = (
                db.query(Task)
                .filter(
                    Task.id == task_id
                )
                .first()
            )

            if not task:
                raise ValueError(
                    f"Task not found: {task_id}"
                )

            task.status = "failed"
            task.error = str(error)
            task.updated_at = self.now()

            attempts = (
                db.query(ExecutionAttempt)
                .filter(
                    ExecutionAttempt.task_id
                    == task_id
                )
                .order_by(
                    ExecutionAttempt.created_at.desc()
                )
                .all()
            )

            if attempts:

                attempt = attempts[0]

                attempt.status = "failed"
                attempt.error = str(error)
                attempt.completed_at = self.now()

            db.commit()

            event_store.emit(
                event_type="TaskFailed",
                task_id=task.id,
                mission_id=task.mission_id,
                session_id=task.session_id,
                status=task.status,
                payload={"error": str(error)},
            )

            return self.serialize_task(
                task
            )

    # ============================================================
    # VERIFY TASK
    # ============================================================

    def verify_task(
        self,
        task_id: str,
        passed: bool,
        evidence: str = ""
    ):

        with SessionLocal() as db:

            task = (
                db.query(Task)
                .filter(
                    Task.id == task_id
                )
                .first()
            )

            if not task:
                raise ValueError(
                    f"Task not found: {task_id}"
                )

            if passed:

                task.verification_status = "verified"

            else:

                task.verification_status = "failed"

            task.updated_at = self.now()

            criteria = (
                db.query(
                    VerificationCriterion
                )
                .filter(
                    VerificationCriterion.task_id
                    == task_id
                )
                .all()
            )

            for criterion in criteria:

                criterion.status = (
                    "passed"
                    if passed
                    else "failed"
                )

                criterion.evidence = evidence

                criterion.verified_at = self.now()

            achievement = None

            if passed:
                # SAGE ONE is currently a single-owner deployment. The owner
                # identity is therefore deployment-scoped rather than stored
                # on every task row. This keeps the verified-result settlement
                # durable without pretending the current schema is multi-tenant.
                owner_key = (
                    f"google:{settings.OWNER_AUTH_SUBJECT}"
                    if settings.OWNER_AUTH_SUBJECT
                    else "developer:local-owner"
                )

                achievement_event, achievement_created = (
                    record_verified_achievement(
                        db,
                        owner_key,
                        VERIFIED_TASK_ACHIEVEMENT,
                        f"Verified mission task: {task.title}",
                        "mission_task",
                        task_id,
                        {
                            "task_id": task_id,
                            "verification_status": "verified",
                            "verification_evidence": evidence,
                            "result": task.result,
                        },
                        commit=False,
                    )
                )

                achievement = {
                    "event_id": achievement_event.id,
                    "created": achievement_created,
                    "amount": achievement_event.amount,
                    "owner_key": owner_key,
                }

            db.commit()

            db.refresh(task)

            result = self.serialize_task(task)
            event_store.emit(
                event_type="VerificationCompleted",
                task_id=task.id,
                mission_id=task.mission_id,
                session_id=task.session_id,
                status=task.verification_status,
                payload={
                    "passed": passed,
                    "evidence": evidence,
                    "achievement": achievement,
                },
            )
            if achievement is not None:
                event_store.emit(
                    event_type="EvolutionAchievementRecorded",
                    task_id=task.id,
                    mission_id=task.mission_id,
                    session_id=task.session_id,
                    status="recorded",
                    payload=achievement,
                )
                result["achievement"] = achievement

            return result

    # ============================================================
    # ADD VERIFICATION CRITERION
    # ============================================================

    def add_verification(
        self,
        mission_id: str,
        description: str,
        task_id: str | None = None,
        criterion_type: str = "semantic",
        expected_value: str | None = None,
        required: bool = True,
    ):

        criterion = VerificationCriterion(
            id=str(uuid.uuid4()),
            mission_id=mission_id,
            task_id=task_id,
            description=description,
            criterion_type=criterion_type,
            expected_value=expected_value,
            required=1 if required else 0,
            status="pending",
            created_at=self.now(),
        )

        with SessionLocal() as db:

            db.add(criterion)
            db.commit()
            db.refresh(criterion)

            return {
                "id": criterion.id,
                "mission_id": criterion.mission_id,
                "task_id": criterion.task_id,
                "description": criterion.description,
                "criterion_type": criterion.criterion_type,
                "expected_value": criterion.expected_value,
                "required": bool(
                    criterion.required
                ),
                "status": criterion.status,
            }

    # ============================================================
    # RECOVERY
    # ============================================================

    def create_recovery(
        self,
        mission_id: str,
        task_id: str,
        failed_attempt_id: str | None,
        strategy: str,
        reason: str
    ):

        recovery = RecoveryAttempt(
            id=str(uuid.uuid4()),
            mission_id=mission_id,
            task_id=task_id,
            failed_attempt_id=failed_attempt_id,
            strategy=strategy,
            reason=reason,
            status="planned",
            created_at=self.now(),
        )

        with SessionLocal() as db:

            db.add(recovery)
            db.commit()
            db.refresh(recovery)

            return {
                "id": recovery.id,
                "mission_id": recovery.mission_id,
                "task_id": recovery.task_id,
                "strategy": recovery.strategy,
                "reason": recovery.reason,
                "status": recovery.status,
            }

    # ============================================================
    # ARTIFACT
    # ============================================================

    def register_artifact(
        self,
        mission_id: str,
        name: str,
        artifact_type: str,
        task_id: str | None = None,
        path: str | None = None,
        uri: str | None = None,
        mime_type: str | None = None,
        size_bytes: int | None = None,
        checksum: str | None = None,
        metadata: dict | None = None,
        verified: bool = False,
    ):

        artifact = Artifact(
            id=str(uuid.uuid4()),
            mission_id=mission_id,
            task_id=task_id,
            name=name,
            artifact_type=artifact_type,
            path=path,
            uri=uri,
            mime_type=mime_type,
            size_bytes=size_bytes,
            checksum=checksum,
            artifact_metadata=(
                json.dumps(metadata)
                if metadata is not None
                else None
            ),
            verified=1 if verified else 0,
            created_at=self.now(),
        )

        with SessionLocal() as db:

            db.add(artifact)
            db.commit()
            db.refresh(artifact)

            return self.serialize_artifact(
                artifact
            )

    # ============================================================
    # MISSION STATUS
    # ============================================================

    def refresh_mission_status(
        self,
        mission_id: str
    ):

        with SessionLocal() as db:

            mission = (
                db.query(Mission)
                .filter(
                    Mission.id == mission_id
                )
                .first()
            )

            if not mission:
                raise ValueError(
                    f"Mission not found: {mission_id}"
                )

            tasks = (
                db.query(Task)
                .filter(
                    Task.mission_id
                    == mission_id
                )
                .all()
            )

            if not tasks:

                mission.status = "planning"

            elif any(
                task.status == "failed"
                for task in tasks
            ):

                mission.status = "failed"

            elif all(
                task.status == "completed"
                and task.verification_status
                == "verified"
                for task in tasks
            ):

                mission.status = "completed"
                mission.verification_status = "verified"
                mission.completed_at = self.now()

            elif any(
                task.status == "running"
                for task in tasks
            ):

                mission.status = "executing"

                mission.verification_status = (
                    "pending"
                )

            else:

                mission.status = "executing"

            mission.updated_at = self.now()

            db.commit()

            db.refresh(mission)

            return self.serialize_mission(
                mission
            )

    # ============================================================
    # SERIALIZERS
    # ============================================================

    @staticmethod
    def serialize_mission(
        mission: Mission
    ):

        return {
            "id": mission.id,
            "goal": mission.goal,
            "status": mission.status,
            "priority": mission.priority,
            "session_id": mission.session_id,
            "current_task_id": mission.current_task_id,
            "plan_version": mission.plan_version,
            "verification_status":
                mission.verification_status,
            "result": mission.result,
            "error": mission.error,
            "created_at":
                mission.created_at.isoformat()
                if mission.created_at
                else None,
            "updated_at":
                mission.updated_at.isoformat()
                if mission.updated_at
                else None,
            "started_at":
                mission.started_at.isoformat()
                if mission.started_at
                else None,
            "completed_at":
                mission.completed_at.isoformat()
                if mission.completed_at
                else None,
        }

    @staticmethod
    def serialize_task(
        task: Task
    ):

        dependencies = []

        if task.depends_on:

            try:

                dependencies = json.loads(
                    task.depends_on
                )

            except Exception:

                dependencies = []

        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "agent": task.agent,
            "session_id": task.session_id,
            "parent_task_id":
                task.parent_task_id,
            "mission_id":
                task.mission_id,
            "depends_on":
                dependencies,
            "progress":
                task.progress,
            "result":
                task.result,
            "error":
                task.error,
            "retries":
                task.retries,
            "max_retries":
                task.max_retries,
            "verification_status":
                task.verification_status,
            "created_at":
                task.created_at.isoformat()
                if task.created_at
                else None,
            "updated_at":
                task.updated_at.isoformat()
                if task.updated_at
                else None,
            "started_at":
                task.started_at.isoformat()
                if task.started_at
                else None,
            "completed_at":
                task.completed_at.isoformat()
                if task.completed_at
                else None,
        }

    @staticmethod
    def serialize_artifact(
        artifact: Artifact
    ):

        return {
            "id": artifact.id,
            "mission_id":
                artifact.mission_id,
            "task_id":
                artifact.task_id,
            "name":
                artifact.name,
            "artifact_type":
                artifact.artifact_type,
            "path":
                artifact.path,
            "uri":
                artifact.uri,
            "mime_type":
                artifact.mime_type,
            "size_bytes":
                artifact.size_bytes,
            "checksum":
                artifact.checksum,
            "metadata":
                artifact.artifact_metadata,
            "verified":
                bool(artifact.verified),
            "created_at":
                artifact.created_at.isoformat()
                if artifact.created_at
                else None,
        }


mission_engine = MissionEngine()