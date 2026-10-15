import json
import re
import uuid

from datetime import datetime, timezone

from brain.router import router

from missions.engine import mission_engine

from database.connection import SessionLocal
from database.repository import repository


EXECUTION_SYSTEM = """
You are the SAGE ONE execution agent.

Your job is to execute ONE mission task using
the real capabilities and context available to you.

CORE RULES:

1. Use real tools when required.
2. Never claim a tool was used unless it was actually used.
3. Never invent tool results.
4. Never invent files, timestamps, actions, or outputs.
5. Tool results are ground truth.
6. Previous verified task outputs are trusted mission context.
7. Use previous task outputs when the current task depends on them.
8. If the required capability does not exist, report that clearly.
9. Do not declare success merely because you produced a plan.
10. Continue using tools until the task is actually completed
    or execution is genuinely blocked.
11. A task may legitimately require NO tool execution if it is
    purely analysis, transformation, validation, comparison,
    or reasoning over already available mission context.
12. Never say that previous task output is unavailable if it
    appears in the supplied mission context.
13. Do not invent missing context.
14. Keep the final report concise.

MISSION CONTEXT is persistent state from earlier tasks.
Treat it as input to the current task.
"""


class ExecutionEngine:

    def __init__(self):

        self.router = router

        self.current_evidence = []
        self.current_action_id = None
        self.current_session_id = None
        self.current_task_id = None
        self.current_mission_id = None
        self.current_owner_authorized = False

    # ---------------------------------------------------------
    # TOOL EXECUTION
    # ---------------------------------------------------------

    def _execute_tool(
        self,
        tool_name: str,
        arguments: dict
    ):

        from tools.registry import registry

        tool = registry.get(
            tool_name
        )

        if not tool:

            evidence = {
                "evidence_id":
                    str(uuid.uuid4()),

                "tool":
                    tool_name,

                "arguments":
                    arguments,

                "success":
                    False,

                "error":
                    f"Tool not found: {tool_name}"
            }

            self.current_evidence.append(
                evidence
            )

            return evidence

        from agentic.engine import action_engine
        from agentic.models import ActionRequest

        result = action_engine.execute(
            ActionRequest(
                tool_name=tool_name,
                arguments=arguments,
                session_id=self.current_session_id,
                task_id=self.current_task_id,
                mission_id=self.current_mission_id,
                parent_action_id=self.current_action_id,
                owner_authorized=self.current_owner_authorized,
                verify=True,
                source="mission_execution",
            )
        ).to_dict()

        self.current_action_id = result.get("action_id")

        evidence = {
            "evidence_id":
                str(uuid.uuid4()),

            "tool":
                tool_name,

            "arguments":
                arguments,

            "success":
                bool(
                    result.get(
                        "success",
                        False
                    )
                ),

            "result":
                result.get(
                    "result"
                ),

            "error":
                result.get(
                    "error"
                ),

            "action_id":
                result.get(
                    "action_id"
                )
        }

        self.current_evidence.append(
            evidence
        )

        return result

    # ---------------------------------------------------------
    # MISSION CONTEXT
    # ---------------------------------------------------------

    def _get_mission_context(
        self,
        mission_id: str,
        current_task_id: str
    ):

        tasks = mission_engine.get_tasks(
            mission_id
        )

        context = []

        for task in tasks:

            if task["id"] == current_task_id:
                continue

            if task.get(
                "status"
            ) != "completed":
                continue

            if task.get(
                "verification_status"
            ) != "verified":
                continue

            context.append(
                {
                    "task_id":
                        task["id"],

                    "title":
                        task["title"],

                    "description":
                        task["description"],

                    "result":
                        task.get(
                            "result"
                        ),

                    "verification_status":
                        task.get(
                            "verification_status"
                        )
                }
            )

        return context

    def _format_mission_context(
        self,
        context
    ):

        if not context:

            return (
                "No previous verified task "
                "outputs are available."
            )

        return json.dumps(
            context,
            indent=2,
            default=str
        )

    # ---------------------------------------------------------
    # EXECUTE ONE TASK
    # ---------------------------------------------------------

    def execute_task(
        self,
        task_id: str,
        *,
        owner_authorized: bool = False,
    ):

        self.current_evidence = []

        started = mission_engine.start_task(
            task_id
        )

        task = started["task"]

        self.current_task_id = task_id
        self.current_mission_id = task.get("mission_id")
        self.current_session_id = task.get("session_id")
        self.current_owner_authorized = bool(owner_authorized)

        attempt_id = started[
            "attempt_id"
        ]

        mission_id = task.get(
            "mission_id"
        )

        if not mission_id:

            mission_engine.fail_task(
                task_id,
                "Task is not attached to a mission."
            )

            return {
                "success": False,
                "task_id": task_id,
                "attempt_id": attempt_id,
                "status": "failed",
                "error":
                    "Task is not attached to a mission."
            }

        mission_context = (
            self._get_mission_context(
                mission_id=mission_id,
                current_task_id=task_id
            )
        )

        from tools.registry import registry

        available_tools = registry.schemas()

        task_prompt = f"""
MISSION TASK

Task ID:
{task["id"]}

Mission ID:
{mission_id}

Title:
{task["title"]}

Description:
{task["description"]}

Agent:
{task["agent"]}

--------------------------------------------------
VERIFIED MISSION CONTEXT FROM PREVIOUS TASKS
--------------------------------------------------

{self._format_mission_context(
    mission_context
)}

--------------------------------------------------
AVAILABLE TOOLS
--------------------------------------------------

{json.dumps(
    available_tools,
    indent=2,
    default=str
)}

--------------------------------------------------
EXECUTION INSTRUCTIONS
--------------------------------------------------

Perform this task using the real available
capabilities.

If previous verified task output contains
information required by this task, USE IT.

Do not claim that previous output is missing
when it is present above.

Use tools if the task requires fresh external
or system information.

If the task is purely validation, comparison,
transformation, or reasoning over previous
verified output, you may complete it without
calling a new tool.

Your final response should clearly state what
was actually accomplished.

Do not invent evidence.
"""

        try:

            result = self.router.think_with_tools(
                system_instruction=
                    EXECUTION_SYSTEM,

                user_message=
                    task_prompt,

                tools=
                    available_tools,

                tool_executor=
                    self._execute_tool,

                conversation=None,

                max_iterations=8
            )

        except Exception as error:

            mission_engine.fail_task(
                task_id,
                str(error)
            )

            return {
                "success": False,
                "task_id": task_id,
                "attempt_id": attempt_id,
                "status": "failed",
                "error":
                    str(error),

                "mission_context":
                    mission_context,

                "evidence":
                    self.current_evidence
            }

        execution_result = {
            "provider":
                result.provider,

            "model":
                result.model,

            "response":
                result.response,

            "mission_context":
                mission_context,

            "evidence":
                list(
                    self.current_evidence
                )
        }

        failed_tools = [
            item
            for item in self.current_evidence
            if not item.get(
                "success",
                False
            )
        ]

        if failed_tools:

            error_text = "; ".join(
                str(
                    item.get(
                        "error",
                        "Unknown tool failure"
                    )
                )
                for item in failed_tools
            )

            mission_engine.fail_task(
                task_id,
                error_text
            )

            return {
                "success": False,
                "task_id": task_id,
                "attempt_id": attempt_id,
                "status": "tool_failed",
                "error":
                    error_text,

                "execution":
                    execution_result
            }

        completed = mission_engine.complete_task(
            task_id,
            execution_result
        )

        verification = self.verify_task(
            task_id,
            execution_result
        )

        if verification["passed"]:

            verified = mission_engine.verify_task(
                task_id,
                passed=True,
                evidence=
                    verification["evidence"]
            )

            return {
                "success": True,

                "task_id":
                    task_id,

                "attempt_id":
                    attempt_id,

                "status":
                    "verified",

                "task":
                    verified,

                "execution":
                    execution_result,

                "verification":
                    verification
            }

        mission_engine.verify_task(
            task_id,
            passed=False,
            evidence=
                verification["evidence"]
        )

        return {
            "success": False,

            "task_id":
                task_id,

            "attempt_id":
                attempt_id,

            "status":
                "verification_failed",

            "task":
                completed,

            "execution":
                execution_result,

            "verification":
                verification
        }

    # ---------------------------------------------------------
    # VERIFICATION
    # ---------------------------------------------------------
    def _get_verification_criteria(self, task_id: str):
        from database.models import VerificationCriterion

        with SessionLocal() as db:
            rows = (
                db.query(VerificationCriterion)
                .filter(VerificationCriterion.task_id == task_id)
                .all()
            )
            return [
                {
                    "id": row.id,
                    "description": row.description,
                    "criterion_type": row.criterion_type,
                    "expected_value": row.expected_value,
                    "required": bool(row.required),
                }
                for row in rows
            ]

    def _deterministic_outcome_verify(
        self,
        *,
        criteria,
        execution_result,
        evidence,
    ):
        if not criteria:
            return {"status": "no_explicit_criteria"}

        from verification.outcome import outcome_verifier

        outcome = outcome_verifier.verify(
            criteria=criteria,
            result=execution_result,
            evidence=evidence,
        )

        # Semantic/manual criteria remain the responsibility of the existing
        # semantic verifier. Deterministic criteria must never be bypassed.
        has_semantic = any(
            str(item.get("criterion_type", "semantic")).lower()
            in {"semantic", "manual"}
            for item in criteria
            if item.get("required", True)
        )

        if not outcome.passed and not has_semantic:
            return {
                "passed": False,
                "status": "failed",
                "evidence": outcome.evidence,
            }

        if outcome.passed and not has_semantic:
            return {
                "passed": True,
                "status": "passed",
                "evidence": outcome.evidence,
            }

        return {"status": "semantic_deferred"}


    def _emit_outcome_event(self, task_id: str, outcome: dict):
        try:
            from events.service import event_store

            task = self._get_task(task_id) or {}
            event_store.emit(
                event_type="OutcomeVerificationCompleted",
                action_id=None,
                session_id=self.current_session_id,
                mission_id=self.current_mission_id,
                task_id=task_id,
                status=outcome.get("status", "unknown"),
                source="outcome_verification",
                payload={
                    "passed": bool(outcome.get("passed", False)),
                    "evidence": outcome.get("evidence"),
                    "task_title": task.get("title"),
                },
            )
        except Exception:
            pass

    def verify_task(
        self,
        task_id: str,
        execution_result: dict
    ):

        task = self._get_task(
            task_id
        )

        if not task:

            return {
                "passed": False,

                "evidence":
                    "Task could not be loaded."
            }

        evidence = execution_result.get(
            "evidence",
            []
        )

        mission_context = execution_result.get(
            "mission_context",
            []
        )

        explicit_criteria = self._get_verification_criteria(task_id)

        outcome = self._deterministic_outcome_verify(
            criteria=explicit_criteria,
            execution_result=execution_result,
            evidence=evidence,
        )

        if outcome["status"] == "failed":
            self._emit_outcome_event(task_id, outcome)
            return outcome

        if outcome["status"] == "passed":
            self._emit_outcome_event(task_id, outcome)
            return outcome

        deterministic = (
            self._deterministic_verify(
                task=task,
                evidence=evidence,
                mission_context=mission_context
            )
        )

        if deterministic is not None:
            self._emit_outcome_event(task_id, deterministic)
            return deterministic

        verification_prompt = f"""
Verify this SAGE ONE mission task.

TASK:
{json.dumps(
    task,
    indent=2,
    default=str
)}

VERIFIED PREVIOUS MISSION CONTEXT:
{json.dumps(
    mission_context,
    indent=2,
    default=str
)}

RAW TOOL EVIDENCE FROM CURRENT TASK:
{json.dumps(
    evidence,
    indent=2,
    default=str
)}

CURRENT EXECUTION REPORT:
{execution_result.get(
    "response",
    ""
)}

IMPORTANT:

The execution report is not sufficient by itself.

Use:

1. Verified previous mission context.
2. Raw tool evidence.
3. The actual task requirements.

Do not reject a task merely because it did not
call a tool.

Some tasks are valid reasoning, validation,
comparison, or transformation tasks that operate
on previous verified task outputs.

Do not accept unsupported claims.

Return ONLY JSON:

{{
  "passed": true,
  "evidence": "specific evidence proving success"
}}

or:

{{
  "passed": false,
  "evidence": "specific missing or contradictory evidence"
}}
"""

        try:

            result = self.router.think(
                system_instruction=(
                    "You are an independent "
                    "verification agent. "
                    "Never assume success. "
                    "Use supplied mission context "
                    "and evidence."
                ),

                user_message=
                    verification_prompt
            )

            parsed = self._parse_json(
                result.response
            )

            passed = bool(
                parsed.get(
                    "passed",
                    False
                )
            )

            evidence_text = str(
                parsed.get(
                    "evidence",
                    ""
                )
            )

            outcome_result = {
                "passed":
                    passed,
                "status":
                    "passed" if passed else "failed",
                "evidence":
                    evidence_text,
                "verifier_provider":
                    result.provider,
                "verifier_model":
                    result.model,
            }

            self._emit_outcome_event(
                task_id,
                outcome_result,
            )

            return outcome_result

        except Exception as error:
            outcome_result = {
                "passed": False,
                "status": "verification_error",
                "evidence":
                    "Verification failed: "
                    + str(error),
            }
            self._emit_outcome_event(task_id, outcome_result)
            return outcome_result

    # ---------------------------------------------------------
    # DETERMINISTIC VERIFICATION
    # ---------------------------------------------------------

    def _deterministic_verify(
        self,
        task: dict,
        evidence: list,
        mission_context: list
    ):

        title = task.get(
            "title",
            ""
        ).lower()

        description = task.get(
            "description",
            ""
        ).lower()

        combined = (
            title
            + " "
            + description
        )

        # -----------------------------------------------------
        # CURRENT UTC TIME
        # -----------------------------------------------------

        if (
            "utc time" in combined
            or "utc timestamp" in combined
            or "current utc" in combined
        ):

            time_evidence = [
                item
                for item in evidence
                if item.get(
                    "tool"
                ) == "sage_time"
            ]

            if not time_evidence:

                return {
                    "passed": False,

                    "evidence":
                        "No sage_time execution evidence exists."
                }

            latest = time_evidence[-1]

            raw_result = latest.get(
                "result"
            )

            if not isinstance(
                raw_result,
                dict
            ):

                return {
                    "passed": False,

                    "evidence":
                        "sage_time returned no structured result."
                }

            timestamp = raw_result.get(
                "utc_time"
            )

            if not timestamp:

                return {
                    "passed": False,

                    "evidence":
                        "sage_time result contains no utc_time field."
                }

            return self._validate_timestamp(
                timestamp
            )

        # -----------------------------------------------------
        # TIMESTAMP FORMAT VALIDATION
        # -----------------------------------------------------

        if (
            "validate timestamp" in combined
            or "timestamp format" in combined
            or "valid utc timestamp" in combined
            or "rfc3339" in combined
        ):

            timestamp = (
                self._find_timestamp_in_context(
                    mission_context
                )
            )

            if not timestamp:

                timestamp = (
                    self._find_timestamp_in_evidence(
                        evidence
                    )
                )

            if not timestamp:

                return {
                    "passed": False,

                    "evidence":
                        (
                            "No timestamp could be "
                            "found in verified mission "
                            "context or current evidence."
                        )
                }

            return self._validate_timestamp(
                timestamp
            )

        # -----------------------------------------------------
        # COMPARE TIMESTAMP WITH SYSTEM CLOCK
        # -----------------------------------------------------

        if (
            "compare" in combined
            and "system clock" in combined
        ) or (
            "within five minutes" in combined
        ):

            timestamp = (
                self._find_timestamp_in_context(
                    mission_context
                )
            )

            if not timestamp:

                return {
                    "passed": False,

                    "evidence":
                        (
                            "No previous verified "
                            "timestamp was available "
                            "for comparison."
                        )
                }

            time_evidence = [
                item
                for item in evidence
                if item.get(
                    "tool"
                ) == "sage_time"
            ]

            if not time_evidence:

                return {
                    "passed": False,

                    "evidence":
                        (
                            "No fresh sage_time result "
                            "was available for comparison."
                        )
                }

            latest = time_evidence[-1]

            raw_result = latest.get(
                "result"
            )

            if not isinstance(
                raw_result,
                dict
            ):

                return {
                    "passed": False,

                    "evidence":
                        "Fresh sage_time result was invalid."
                }

            verification_timestamp = raw_result.get(
                "utc_time"
            )

            if not verification_timestamp:

                return {
                    "passed": False,

                    "evidence":
                        (
                            "Fresh sage_time result "
                            "contains no utc_time."
                        )
                }

            try:

                original_time = (
                    self._parse_timestamp(
                        timestamp
                    )
                )

                verification_time = (
                    self._parse_timestamp(
                        verification_timestamp
                    )
                )

            except Exception as error:

                return {
                    "passed": False,

                    "evidence":
                        (
                            "Timestamp comparison "
                            "failed: "
                            + str(error)
                        )
                }

            difference = abs(
                (
                    verification_time
                    -
                    original_time
                ).total_seconds()
            )

            if difference > 300:

                return {
                    "passed": False,

                    "evidence":
                        (
                            "Timestamp differs from "
                            f"verification time by "
                            f"{difference:.2f} seconds, "
                            "which exceeds five minutes."
                        )
                }

            return {
                "passed": True,

                "evidence":
                    (
                        "Deterministic verification passed. "
                        f"Original timestamp: {timestamp}. "
                        f"Verification timestamp: "
                        f"{verification_timestamp}. "
                        f"Difference: {difference:.2f} seconds."
                    ),

                "verification_type":
                    "deterministic"
            }

        return None

    # ---------------------------------------------------------
    # TIMESTAMP HELPERS
    # ---------------------------------------------------------

    @staticmethod
    def _parse_timestamp(
        timestamp: str
    ):

        parsed = datetime.fromisoformat(
            timestamp.replace(
                "Z",
                "+00:00"
            )
        )

        if parsed.tzinfo is None:

            raise ValueError(
                "Timestamp has no timezone."
            )

        return parsed.astimezone(
            timezone.utc
        )

    def _validate_timestamp(
        self,
        timestamp: str
    ):

        try:

            parsed_time = (
                self._parse_timestamp(
                    timestamp
                )
            )

        except Exception as error:

            return {
                "passed": False,

                "evidence":
                    (
                        "Returned timestamp is not "
                        "a valid timezone-aware "
                        f"ISO 8601 timestamp: {error}"
                    )
            }

        return {
            "passed": True,

            "evidence":
                (
                    "Deterministic verification passed. "
                    f"The timestamp {timestamp} is a valid "
                    "timezone-aware ISO 8601 timestamp "
                    f"representing UTC as "
                    f"{parsed_time.isoformat()}."
                ),

            "verification_type":
                "deterministic"
        }

    @staticmethod
    def _find_timestamp_in_context(
        mission_context: list
    ):

        timestamp_pattern = re.compile(
            r"\d{4}-\d{2}-\d{2}T"
            r"\d{2}:\d{2}:\d{2}"
            r"(?:\.\d+)?"
            r"(?:Z|[+-]\d{2}:\d{2})"
        )

        for item in reversed(
            mission_context
        ):

            serialized = json.dumps(
                item,
                default=str
            )

            match = timestamp_pattern.search(
                serialized
            )

            if match:

                return match.group(
                    0
                )

        return None

    @staticmethod
    def _find_timestamp_in_evidence(
        evidence: list
    ):

        timestamp_pattern = re.compile(
            r"\d{4}-\d{2}-\d{2}T"
            r"\d{2}:\d{2}:\d{2}"
            r"(?:\.\d+)?"
            r"(?:Z|[+-]\d{2}:\d{2})"
        )

        for item in reversed(
            evidence
        ):

            serialized = json.dumps(
                item,
                default=str
            )

            match = timestamp_pattern.search(
                serialized
            )

            if match:

                return match.group(
                    0
                )

        return None

    # ---------------------------------------------------------
    # MISSION EXECUTION
    # ---------------------------------------------------------

    def execute_next(
        self,
        mission_id: str,
        *,
        owner_authorized: bool = False,
    ):

        ready = mission_engine.get_ready_tasks(
            mission_id
        )

        if not ready:

            mission = (
                mission_engine.refresh_mission_status(
                    mission_id
                )
            )

            return {
                "success": False,

                "status":
                    mission["status"],

                "message":
                    "No executable task is currently ready.",

                "mission":
                    mission
            }

        task = ready[0]

        result = self.execute_task(
            task["id"],
            owner_authorized=owner_authorized,
        )

        mission = (
            mission_engine.refresh_mission_status(
                mission_id
            )
        )

        return {
            "success":
                result.get(
                    "success",
                    False
                ),

            "task":
                result,

            "mission":
                mission
        }

    def execute_mission(
        self,
        mission_id: str,
        max_steps: int = 20,
        *,
        owner_authorized: bool = False,
    ):

        history = []

        for _ in range(
            max_steps
        ):

            mission = (
                mission_engine.refresh_mission_status(
                    mission_id
                )
            )

            if mission["status"] == "completed":

                return {
                    "success": True,

                    "status":
                        "completed",

                    "mission":
                        mission,

                    "history":
                        history
                }

            if mission["status"] == "failed":

                return {
                    "success": False,

                    "status":
                        "failed",

                    "mission":
                        mission,

                    "history":
                        history
                }

            ready = mission_engine.get_ready_tasks(
                mission_id
            )

            if not ready:

                return {
                    "success": False,

                    "status":
                        "blocked",

                    "mission":
                        mission,

                    "history":
                        history
                }

            task_result = self.execute_task(
                ready[0]["id"],
                owner_authorized=owner_authorized,
            )

            history.append(
                task_result
            )

            if not task_result.get(
                "success",
                False
            ):

                return {
                    "success": False,

                    "status":
                        task_result.get(
                            "status",
                            "failed"
                        ),

                    "mission":
                        mission_engine.refresh_mission_status(
                            mission_id
                        ),

                    "history":
                        history
                }

        return {
            "success": False,

            "status":
                "max_steps_reached",

            "mission":
                mission_engine.refresh_mission_status(
                    mission_id
                ),

            "history":
                history
        }

    # ---------------------------------------------------------
    # DATABASE
    # ---------------------------------------------------------

    @staticmethod
    def _get_task(
        task_id: str
    ):

        with SessionLocal() as db:

            task = repository.get_task(
                db,
                task_id
            )

            if not task:

                return None

            return mission_engine.serialize_task(
                task
            )

    # ---------------------------------------------------------
    # JSON
    # ---------------------------------------------------------

    @staticmethod
    def _parse_json(
        response: str
    ):

        text = response.strip()

        if text.startswith(
            "```"
        ):

            lines = text.splitlines()

            if lines:

                lines = lines[1:]

            if (
                lines
                and
                lines[-1].strip()
                == "```"
            ):

                lines = lines[:-1]

            text = "\n".join(
                lines
            )

        return json.loads(
            text
        )


execution_engine = ExecutionEngine()