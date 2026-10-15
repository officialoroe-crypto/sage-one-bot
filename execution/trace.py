from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from database.connection import SessionLocal
from database.models import (
    Mission,
    Task,
    ExecutionAttempt,
    VerificationCriterion,
    Artifact,
    RecoveryAttempt,
    ActionLog,
    ActionEvidence,
)


def _iso(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)

        return value.isoformat()

    return str(value)


def _safe_json(value):
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {
            str(key): _safe_json(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            _safe_json(item)
            for item in value
        ]

    return str(value)


def _model_dict(obj, fields):
    if obj is None:
        return None

    result = {}

    for field in fields:
        value = getattr(obj, field, None)

        if isinstance(value, datetime):
            value = _iso(value)
        else:
            value = _safe_json(value)

        result[field] = value

    return result


def _parse_json(value):
    """
    Safely parse JSON strings stored in task/attempt results.
    """
    if value is None:
        return None

    if isinstance(value, (dict, list)):
        return value

    if not isinstance(value, str):
        return value

    try:
        return json.loads(value)
    except Exception:
        return value


def _find_action_ids(value):
    """
    Recursively search any task/attempt result for action_id fields.
    """

    found = set()

    if value is None:
        return found

    if isinstance(value, str):
        parsed = _parse_json(value)

        if parsed != value:
            return _find_action_ids(parsed)

        return found

    if isinstance(value, dict):

        action_id = value.get("action_id")

        if action_id:
            found.add(str(action_id))

        for item in value.values():
            found.update(
                _find_action_ids(item)
            )

        return found

    if isinstance(value, list):

        for item in value:
            found.update(
                _find_action_ids(item)
            )

        return found

    return found


class ExecutionTraceService:
    """
    Builds the persistent SAGE ONE execution trace.

    The database remains the source of truth.

    Trace structure:

        Mission
          |
          +-- Task
                |
                +-- Execution Attempts
                |
                +-- Tool Actions
                |
                +-- Verification
                |
                +-- Artifacts
                |
                +-- Recovery

    Tool actions are correlated in two ways:

    1. Direct task_id relationship.
    2. action_id embedded in execution evidence.

    The second path is important for older executions where
    ActionLog.task_id was not populated.
    """

    def get_mission_trace(
        self,
        mission_id: str,
    ) -> dict[str, Any]:

        db = SessionLocal()

        try:
            mission = db.get(
                Mission,
                mission_id,
            )

            if mission is None:
                return {
                    "success": False,
                    "error": "Mission not found",
                    "mission_id": mission_id,
                }

            tasks = db.scalars(
                select(Task)
                .where(
                    Task.mission_id == mission_id
                )
                .order_by(
                    Task.created_at.asc()
                )
            ).all()

            task_traces = []

            for task in tasks:

                task_id = task.id

                attempts = db.scalars(
                    select(ExecutionAttempt)
                    .where(
                        ExecutionAttempt.task_id
                        == task_id
                    )
                    .order_by(
                        ExecutionAttempt.attempt_number.asc()
                    )
                ).all()

                direct_actions = db.scalars(
                    select(ActionLog)
                    .where(
                        ActionLog.task_id
                        == task_id
                    )
                    .order_by(
                        ActionLog.started_at.asc()
                    )
                ).all()

                verifications = db.scalars(
                    select(VerificationCriterion)
                    .where(
                        VerificationCriterion.task_id
                        == task_id
                    )
                    .order_by(
                        VerificationCriterion.created_at.asc()
                    )
                ).all()

                artifacts = db.scalars(
                    select(Artifact)
                    .where(
                        Artifact.task_id
                        == task_id
                    )
                    .order_by(
                        Artifact.created_at.asc()
                    )
                ).all()

                recoveries = db.scalars(
                    select(RecoveryAttempt)
                    .where(
                        RecoveryAttempt.task_id
                        == task_id
                    )
                    .order_by(
                        RecoveryAttempt.created_at.asc()
                    )
                ).all()

                action_evidence = db.scalars(
                    select(ActionEvidence)
                    .where(
                        ActionEvidence.task_id
                        == task_id
                    )
                    .order_by(
                        ActionEvidence.created_at.asc()
                    )
                ).all()

                # ------------------------------------------------
                # Find action IDs stored inside execution evidence
                # ------------------------------------------------

                action_ids = set()

                action_ids.update(
                    _find_action_ids(
                        getattr(
                            task,
                            "result",
                            None,
                        )
                    )
                )

                action_ids.update(
                    _find_action_ids(
                        getattr(
                            task,
                            "error",
                            None,
                        )
                    )
                )

                for attempt in attempts:
                    action_ids.update(
                        _find_action_ids(
                            getattr(
                                attempt,
                                "result",
                                None,
                            )
                        )
                    )

                    action_ids.update(
                        _find_action_ids(
                            getattr(
                                attempt,
                                "error",
                                None,
                            )
                        )
                    )

                # ------------------------------------------------
                # Load actions referenced by action_id
                # ------------------------------------------------

                correlated_actions = []

                if action_ids:

                    all_actions = db.scalars(
                        select(ActionLog)
                        .where(
                            ActionLog.id.in_(
                                list(action_ids)
                            )
                        )
                    ).all()

                    correlated_actions.extend(
                        all_actions
                    )

                # ------------------------------------------------
                # Merge direct + correlated actions
                # ------------------------------------------------

                action_map = {}

                for action in direct_actions:
                    action_map[
                        str(action.id)
                    ] = action

                for action in correlated_actions:
                    action_map[
                        str(action.id)
                    ] = action

                actions = sorted(
                    action_map.values(),
                    key=lambda item: (
                        item.started_at
                        or datetime.min
                    ),
                )

                task_traces.append(
                    {
                        "task": _model_dict(
                            task,
                            [
                                "id",
                                "title",
                                "description",
                                "status",
                                "priority",
                                "agent",
                                "session_id",
                                "parent_task_id",
                                "mission_id",
                                "depends_on",
                                "progress",
                                "result",
                                "error",
                                "retries",
                                "max_retries",
                                "verification_status",
                                "created_at",
                                "updated_at",
                                "started_at",
                                "completed_at",
                            ],
                        ),

                        "attempts": [
                            _model_dict(
                                attempt,
                                [
                                    "id",
                                    "mission_id",
                                    "task_id",
                                    "attempt_number",
                                    "status",
                                    "agent",
                                    "action_summary",
                                    "result",
                                    "error",
                                    "created_at",
                                    "completed_at",
                                ],
                            )
                            for attempt in attempts
                        ],

                        "actions": [
                            _model_dict(
                                action,
                                [
                                    "id",
                                    "session_id",
                                    "task_id",
                                    "tool",
                                    "capability",
                                    "permission",
                                    "risk",
                                    "arguments",
                                    "permission_allowed",
                                    "permission_reason",
                                    "status",
                                    "result",
                                    "error",
                                    "started_at",
                                    "completed_at",
                                    "duration_ms",
                                ],
                            )
                            for action in actions
                        ],

                        "verification": [
                            _model_dict(
                                verification,
                                [
                                    "id",
                                    "mission_id",
                                    "task_id",
                                    "description",
                                    "criterion_type",
                                    "expected_value",
                                    "required",
                                    "status",
                                    "evidence",
                                    "verified_at",
                                    "created_at",
                                ],
                            )
                            for verification in verifications
                        ],

                        "artifacts": [
                            _model_dict(
                                artifact,
                                [
                                    "id",
                                    "mission_id",
                                    "task_id",
                                    "name",
                                    "artifact_type",
                                    "path",
                                    "uri",
                                    "mime_type",
                                    "size_bytes",
                                    "checksum",
                                    "metadata",
                                    "verified",
                                    "created_at",
                                ],
                            )
                            for artifact in artifacts
                        ],

                        "recovery": [
                            _model_dict(
                                recovery,
                                [
                                    "id",
                                    "mission_id",
                                    "task_id",
                                    "failed_attempt_id",
                                    "strategy",
                                    "reason",
                                    "status",
                                    "result",
                                    "created_at",
                                    "completed_at",
                                ],
                            )
                            for recovery in recoveries
                        ],

                        "evidence": [
                            _model_dict(
                                item,
                                [
                                    "id",
                                    "action_id",
                                    "mission_id",
                                    "task_id",
                                    "parent_action_id",
                                    "evidence_type",
                                    "content",
                                    "verified",
                                    "created_at",
                                ],
                            )
                            for item in action_evidence
                        ],
                    }
                )

            summary = self._build_summary(
                mission,
                task_traces,
            )

            return {
                "success": True,
                "trace_version": "1.1",

                "trace_generated_at": datetime.now(
                    timezone.utc
                ).isoformat(),

                "mission": _model_dict(
                    mission,
                    [
                        "id",
                        "goal",
                        "status",
                        "priority",
                        "session_id",
                        "current_task_id",
                        "plan_version",
                        "verification_status",
                        "result",
                        "error",
                        "created_at",
                        "updated_at",
                        "started_at",
                        "completed_at",
                    ],
                ),

                "tasks": task_traces,

                "summary": summary,
            }

        except Exception as exc:

            return {
                "success": False,
                "error": str(exc),
                "mission_id": mission_id,
            }

        finally:
            db.close()

    def get_mission_result(
        self,
        mission_id: str,
    ) -> dict[str, Any]:

        trace = self.get_mission_trace(
            mission_id
        )

        if not trace.get("success"):
            return trace

        mission = (
            trace.get("mission")
            or {}
        )

        tasks = (
            trace.get("tasks")
            or []
        )

        summary = (
            trace.get("summary")
            or {}
        )

        return {
            "success": True,
            "mission_id": mission_id,

            "status": mission.get(
                "status"
            ),

            "verification_status": (
                mission.get(
                    "verification_status"
                )
            ),

            "result": mission.get(
                "result"
            ),

            "error": mission.get(
                "error"
            ),

            "summary": summary,

            "tasks": [
                {
                    "id": (
                        node.get("task")
                        or {}
                    ).get("id"),

                    "title": (
                        node.get("task")
                        or {}
                    ).get("title"),

                    "status": (
                        node.get("task")
                        or {}
                    ).get("status"),

                    "verification_status": (
                        node.get("task")
                        or {}
                    ).get(
                        "verification_status"
                    ),

                    "result": (
                        node.get("task")
                        or {}
                    ).get("result"),

                    "error": (
                        node.get("task")
                        or {}
                    ).get("error"),

                    "attempts": node.get(
                        "attempts",
                        [],
                    ),

                    "actions": node.get(
                        "actions",
                        [],
                    ),

                    "verification": node.get(
                        "verification",
                        [],
                    ),

                    "artifacts": node.get(
                        "artifacts",
                        [],
                    ),

                    "recovery": node.get(
                        "recovery",
                        [],
                    ),
                    "evidence": node.get(
                        "evidence",
                        [],
                    ),
                }
                for node in tasks
            ],
        }

    def _build_summary(
        self,
        mission,
        task_traces,
    ) -> dict[str, Any]:

        total_tasks = len(
            task_traces
        )

        completed_tasks = 0
        verified_tasks = 0
        failed_tasks = 0

        total_attempts = 0
        total_actions = 0
        successful_actions = 0
        failed_actions = 0

        total_artifacts = 0
        total_recoveries = 0
        total_evidence = 0
        verified_evidence = 0

        for node in task_traces:

            task = (
                node.get("task")
                or {}
            )

            if task.get(
                "status"
            ) == "completed":

                completed_tasks += 1

            if task.get(
                "verification_status"
            ) == "verified":

                verified_tasks += 1

            if task.get(
                "status"
            ) == "failed":

                failed_tasks += 1

            attempts = node.get(
                "attempts",
                [],
            )

            actions = node.get(
                "actions",
                [],
            )

            artifacts = node.get(
                "artifacts",
                [],
            )

            recoveries = node.get(
                "recovery",
                [],
            )
            evidence = node.get(
                "evidence",
                [],
            )

            total_attempts += len(
                attempts
            )

            total_actions += len(
                actions
            )

            total_artifacts += len(
                artifacts
            )

            total_recoveries += len(
                recoveries
            )
            total_evidence += len(evidence)
            verified_evidence += sum(
                1 for item in evidence if item.get("verified")
            )

            for action in actions:

                status = action.get(
                    "status"
                )

                if status == "completed":
                    successful_actions += 1

                elif status == "failed":
                    failed_actions += 1

        mission_status = getattr(
            mission,
            "status",
            None,
        )

        mission_verification = getattr(
            mission,
            "verification_status",
            None,
        )

        if (
            mission_status == "completed"
            and mission_verification
            == "verified"
        ):

            execution_integrity = (
                "verified"
            )

        elif mission_status == "failed":

            execution_integrity = (
                "failed"
            )

        else:

            execution_integrity = (
                "incomplete"
            )

        return {
            "mission_status": (
                mission_status
            ),

            "mission_verification": (
                mission_verification
            ),

            "execution_integrity": (
                execution_integrity
            ),

            "total_tasks": (
                total_tasks
            ),

            "completed_tasks": (
                completed_tasks
            ),

            "verified_tasks": (
                verified_tasks
            ),

            "failed_tasks": (
                failed_tasks
            ),

            "total_attempts": (
                total_attempts
            ),

            "total_actions": (
                total_actions
            ),

            "successful_actions": (
                successful_actions
            ),

            "failed_actions": (
                failed_actions
            ),

            "total_artifacts": (
                total_artifacts
            ),

            "total_recoveries": (
                total_recoveries
            ),
            "total_evidence": total_evidence,
            "verified_evidence": verified_evidence,
        }


execution_trace = (
    ExecutionTraceService()
)