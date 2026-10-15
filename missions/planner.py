import json
import re

from brain.router import router

from missions.engine import mission_engine


PLANNER_SYSTEM = """
You are the SAGE ONE mission planner.

Your job is to convert a user's high-level goal
into an executable mission plan.

Do NOT execute anything.

Create a practical task graph.

Each task must:

- have a clear title
- explain exactly what must be done
- identify the appropriate agent
- have a priority
- optionally depend on earlier task IDs
- define how the task can later be verified

CRITICAL PLANNING RULES:

1. Plan around REAL capabilities and REAL tools.

2. Never invent a tool.

3. Never invent a capability.

4. Never invent an agent that does not correspond
   to a known SAGE capability.

5. Do not impose arbitrary formatting requirements
   unless the user's goal explicitly requires them.

6. Do not silently narrow a user's goal.

7. Preserve the actual meaning of the user's request.

8. Prefer standards-compliant validation over
   arbitrary exact string matching.

9. If a timestamp, URL, email, file, number,
   identifier, or other structured value must be
   validated, validate its semantic correctness
   and standards compliance rather than inventing
   a narrower format.

10. Separate planning from execution.

11. Do not claim work has been completed.

12. Complex goals should be decomposed into
    multiple concrete tasks.

13. Independent tasks may exist in parallel.

14. Tasks that require previous results must depend
    on those previous tasks.

15. The final task should normally verify the
    overall mission result.

16. Verification criteria must be objectively
    checkable whenever possible.

17. Do not create a verification requirement that
    contradicts the actual output format of an
    available tool.

18. If the user's goal can be verified
    deterministically, prefer deterministic
    verification criteria.

19. Do not add unnecessary tasks merely to make
    the mission look complex.

20. The mission should be executable with the
    capabilities actually available to SAGE.

Return ONLY JSON in this structure:

{
  "mission_summary": "short description",
  "tasks": [
    {
      "id": "task_1",
      "title": "Task title",
      "description": "Detailed task description",
      "agent": "general",
      "priority": 1,
      "depends_on": [],
      "verification": [
        "What must be true when this task succeeds"
      ]
    }
  ],
  "mission_verification": [
    "Condition proving the overall mission succeeded"
  ]
}

IMPORTANT:

When the user asks for a timestamp, do not
automatically require the literal format
YYYY-MM-DDTHH:MM:SSZ.

A valid UTC timestamp may include fractional
seconds and may represent UTC using +00:00 or Z,
provided it is a valid standards-compliant
timestamp.

Only require second precision or a literal Z
suffix when the user's actual goal explicitly
requires that representation.
"""


class MissionPlanner:

    def __init__(self):
        self.router = router

    def plan(
        self,
        goal: str,
        session_id: str | None = None,
        priority: int = 3,
    ):

        if not goal or not goal.strip():

            raise ValueError(
                "Mission goal cannot be empty."
            )

        result = self.router.think(
            system_instruction=PLANNER_SYSTEM,
            user_message=goal.strip(),
        )

        plan = self._parse_json(
            result.response
        )

        self._validate_plan(
            plan
        )

        mission = mission_engine.create_mission(
            goal=goal.strip(),
            session_id=session_id,
            priority=priority,
        )

        mission_id = mission["id"]

        created_tasks = {}

        for index, task_data in enumerate(
            plan["tasks"],
            start=1
        ):

            temporary_dependencies = (
                task_data.get(
                    "depends_on",
                    []
                )
                or []
            )

            real_dependencies = []

            for dependency in temporary_dependencies:

                dependency_id = created_tasks.get(
                    dependency
                )

                if dependency_id:
                    real_dependencies.append(
                        dependency_id
                    )

            task = mission_engine.create_task(
                mission_id=mission_id,
                title=task_data.get(
                    "title",
                    f"Mission task {index}"
                ),
                description=task_data.get(
                    "description",
                    ""
                ),
                priority=int(
                    task_data.get(
                        "priority",
                        index
                    )
                ),
                agent=task_data.get(
                    "agent",
                    "general"
                ),
                depends_on=real_dependencies,
            )

            temporary_id = task_data.get(
                "id",
                f"task_{index}"
            )

            created_tasks[
                temporary_id
            ] = task["id"]

            verification_items = (
                task_data.get(
                    "verification",
                    []
                )
                or []
            )

            for criterion in verification_items:

                mission_engine.add_verification(
                    mission_id=mission_id,
                    task_id=task["id"],
                    description=str(
                        criterion
                    ),
                    criterion_type="semantic",
                    required=True,
                )

        mission_verification = (
            plan.get(
                "mission_verification",
                []
            )
            or []
        )

        for criterion in mission_verification:

            mission_engine.add_verification(
                mission_id=mission_id,
                description=str(criterion),
                criterion_type="mission",
                required=True,
            )

        mission_status = (
            mission_engine.refresh_mission_status(
                mission_id
            )
        )

        return {
            "mission": mission_status,
            "plan": {
                "summary":
                    plan.get(
                        "mission_summary",
                        ""
                    ),
                "task_count":
                    len(plan["tasks"]),
                "tasks":
                    mission_engine.get_tasks(
                        mission_id
                    ),
                "mission_verification":
                    mission_verification,
            },
            "planner": {
                "provider":
                    result.provider,
                "model":
                    result.model,
            },
        }

    @staticmethod
    def _parse_json(
        response: str
    ):

        text = response.strip()

        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE
        )

        text = re.sub(
            r"\s*```$",
            "",
            text
        )

        try:

            return json.loads(
                text
            )

        except json.JSONDecodeError:

            match = re.search(
                r"\{.*\}",
                text,
                flags=re.DOTALL
            )

            if not match:

                raise ValueError(
                    "Planner returned invalid JSON."
                )

            try:

                return json.loads(
                    match.group(0)
                )

            except json.JSONDecodeError as error:

                raise ValueError(
                    "Planner returned malformed JSON: "
                    + str(error)
                )

    @staticmethod
    def _validate_plan(
        plan: dict
    ):

        if not isinstance(
            plan,
            dict
        ):

            raise ValueError(
                "Planner output must be an object."
            )

        tasks = plan.get(
            "tasks"
        )

        if not isinstance(
            tasks,
            list
        ) or not tasks:

            raise ValueError(
                "Planner returned no executable tasks."
            )

        seen_ids = set()

        for task in tasks:

            if not isinstance(
                task,
                dict
            ):

                raise ValueError(
                    "Every planner task must be an object."
                )

            task_id = task.get(
                "id"
            )

            if not task_id:

                raise ValueError(
                    "Every planner task needs an id."
                )

            if task_id in seen_ids:

                raise ValueError(
                    f"Duplicate planner task id: {task_id}"
                )

            seen_ids.add(
                task_id
            )

            if not task.get(
                "title"
            ):

                raise ValueError(
                    f"Task {task_id} has no title."
                )

            if not task.get(
                "description"
            ):

                raise ValueError(
                    f"Task {task_id} has no description."
                )

            dependencies = task.get(
                "depends_on",
                []
            )

            if not isinstance(
                dependencies,
                list
            ):

                raise ValueError(
                    f"Task {task_id} dependencies "
                    "must be a list."
                )

            for dependency in dependencies:

                if dependency not in seen_ids:

                    raise ValueError(
                        f"Task {task_id} depends on "
                        f"unknown or future task: "
                        f"{dependency}"
                    )

        if not isinstance(
            plan.get(
                "mission_verification",
                []
            ),
            list
        ):

            raise ValueError(
                "mission_verification must be a list."
            )


planner = MissionPlanner()