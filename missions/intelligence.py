"""Mission-level control, synthesis, and recovery policy.

This module keeps mission intelligence separate from task execution so the
executor can remain deterministic and the durable worker can own lifecycle.
"""

import json
import uuid

from datetime import datetime, timezone

from brain.router import router
from database.connection import SessionLocal
from database.models import Mission, Task
from missions.engine import mission_engine


CONTROLLED_STATUSES = {"paused", "cancelled"}
TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


RESULT_SCHEMA = {
    "type": "object",
    "required": ["summary", "key_results", "next_actions", "confidence"],
    "properties": {
        "summary": {"type": "string"},
        "key_results": {"type": "array"},
        "next_actions": {"type": "array"},
        "confidence": {"type": "string"},
    },
}


RESULT_SYSTEM = """
You are the SAGE ONE mission result synthesizer.

Synthesize ONLY from verified task outputs supplied in the mission context.
Never invent work, evidence, facts, files, tools, or outcomes.
If a task failed or output is incomplete, say so explicitly.
Keep the result practical and concise.
Return JSON only with summary, key_results, next_actions, confidence.
"""


class MissionIntelligence:
    """Own mission-level controls, recovery policy, and final synthesis."""

    @staticmethod
    def now():
        return datetime.now(timezone.utc)

    def get_status(self, mission_id: str):
        mission = mission_engine.get_mission(mission_id)
        if mission is None:
            raise ValueError(f"Mission not found: {mission_id}")
        return mission["status"]

    def set_status(self, mission_id: str, status: str):
        if status not in {"paused", "cancelled", "resumed"}:
            raise ValueError(f"Unsupported mission control status: {status}")

        with SessionLocal() as db:
            mission = db.query(Mission).filter(Mission.id == mission_id).first()
            if mission is None:
                raise ValueError(f"Mission not found: {mission_id}")

            current = mission.status
            if status == "paused":
                if current not in {"planning", "executing"}:
                    raise ValueError(f"Mission cannot pause from status: {current}")
                mission.status = "paused"
                mission.updated_at = self.now()
            elif status == "cancelled":
                if current in TERMINAL_STATUSES:
                    raise ValueError(f"Mission cannot cancel from status: {current}")
                mission.status = "cancelled"
                mission.error = "Mission cancelled by user."
                mission.updated_at = self.now()
            else:
                if current != "paused":
                    raise ValueError(f"Mission cannot resume from status: {current}")
                mission.status = "executing"
                mission.error = None
                mission.updated_at = self.now()

            db.commit()
            db.refresh(mission)
            return mission_engine.serialize_mission(mission)

    def should_continue(self, mission_id: str) -> bool:
        status = self.get_status(mission_id)
        return status not in CONTROLLED_STATUSES and status not in {"completed", "failed"}

    def recovery_strategy(self, task: dict, error: str) -> dict:
        """Choose a deterministic recovery action without another model call."""
        retries = int(task.get("retries") or 0)
        max_retries = int(task.get("max_retries") or 0)
        if retries < max_retries:
            strategy = "retry"
        elif task.get("agent") == "research":
            strategy = "research_retry_with_fresh_context"
        elif task.get("agent") in {"business", "creative"}:
            strategy = "replan_task"
        else:
            strategy = "escalate"

        return {
            "strategy": strategy,
            "reason": str(error),
            "retryable": strategy in {"retry", "research_retry_with_fresh_context"},
            "retries": retries,
            "max_retries": max_retries,
        }

    def create_recovery_record(self, task: dict, strategy: dict) -> dict:
        return mission_engine.create_recovery(
            mission_id=task["mission_id"],
            task_id=task["id"],
            failed_attempt_id=None,
            strategy=strategy["strategy"],
            reason=strategy["reason"],
        )

    def prepare_retry(self, task_id: str, reason: str) -> dict:
        """Reset a failed mission task into a durable pending retry state."""
        with SessionLocal() as db:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task is None:
                raise ValueError(f"Task not found: {task_id}")
            if task.retries >= task.max_retries:
                raise ValueError(f"Task retry limit reached: {task_id}")

            task.retries += 1
            task.status = "pending"
            task.progress = 0
            task.verification_status = "pending"
            task.error = str(reason)
            task.next_retry_at = self.now()
            task.updated_at = self.now()
            task.completed_at = None
            db.commit()
            db.refresh(task)
            return mission_engine.serialize_task(task)

    @staticmethod
    def _verified_context(tasks: list[dict]) -> list[dict]:
        return [
            {
                "task_id": task["id"],
                "title": task["title"],
                "agent": task.get("agent"),
                "result": task.get("result"),
                "verification_status": task.get("verification_status"),
            }
            for task in tasks
            if task.get("status") == "completed"
            and task.get("verification_status") == "verified"
        ]

    @staticmethod
    def _fallback(tasks: list[dict], failed: list[dict]) -> dict:
        verified = MissionIntelligence._verified_context(tasks)
        return {
            "summary": (
                f"Mission completed with {len(verified)} verified task result(s)."
                if not failed
                else f"Mission produced {len(verified)} verified result(s) and {len(failed)} failed task(s)."
            ),
            "key_results": [
                {
                    "task_id": item["task_id"],
                    "title": item["title"],
                    "result": item.get("result"),
                }
                for item in verified
            ],
            "next_actions": [
                f"Review failed task: {task['title']}"
                for task in failed
            ],
            "confidence": "high" if verified and not failed else "partial",
        }

    def synthesize(self, mission_id: str, use_model: bool = True) -> dict:
        mission = mission_engine.get_mission(mission_id)
        if mission is None:
            raise ValueError(f"Mission not found: {mission_id}")

        tasks = mission_engine.get_tasks(mission_id)
        failed = [task for task in tasks if task.get("status") == "failed"]
        verified = self._verified_context(tasks)
        fallback = self._fallback(tasks, failed)

        if not verified:
            result = fallback
        elif not use_model:
            result = fallback
        else:
            context = json.dumps(
                {
                    "mission_goal": mission["goal"],
                    "verified_tasks": verified,
                    "failed_tasks": failed,
                },
                indent=2,
                default=str,
            )
            try:
                response = router.think_structured(
                    system_instruction=RESULT_SYSTEM,
                    user_message=context,
                    schema=RESULT_SCHEMA,
                    schema_name="sage_mission_result",
                )
                result = response.data
            except Exception:
                result = fallback

        with SessionLocal() as db:
            row = db.query(Mission).filter(Mission.id == mission_id).first()
            if row is None:
                raise ValueError(f"Mission not found: {mission_id}")
            row.result = json.dumps(result, default=str)
            row.updated_at = self.now()
            db.commit()

        return {
            "mission_id": mission_id,
            "result": result,
            "verified_task_count": len(verified),
            "failed_task_count": len(failed),
            "synthesis_id": str(uuid.uuid4()),
        }


mission_intelligence = MissionIntelligence()
