from datetime import datetime, timezone
from typing import Any

from app.core import sage
from agents.manager import agents
from tasks.engine import tasks


class SageOrchestrator:
    """Coordinate goal planning and durable task execution."""

    def __init__(self):
        self.name = "SAGE ORCHESTRATOR"
        self.max_steps = 10

    def execute_goal(self, goal: str, session_id: str | None = None, priority: int = 3, task_id: str | None = None, worker_id: str | None = None) -> dict[str, Any]:
        if not goal or not goal.strip():
            raise ValueError("Goal cannot be empty.")
        goal = goal.strip()
        agent_name = agents.choose(goal)
        if not agents.exists(agent_name):
            agent_name = "general"
        worker_owned = task_id is not None and worker_id is not None
        if worker_owned:
            resolved_task_id = task_id
        else:
            root_task = tasks.create(title=goal[:120], description=goal, priority=priority, agent=agent_name, session_id=session_id)
            resolved_task_id = root_task["id"]
            tasks.start(resolved_task_id)
        plan = self.plan(goal=goal, agent_name=agent_name)[: self.max_steps]
        results: list[dict[str, Any]] = []
        total_steps = max(len(plan), 1)
        for index, step in enumerate(plan, start=1):
            progress = int(((index - 1) / total_steps) * 100)
            progress_result = tasks.progress(resolved_task_id, progress)
            if worker_owned and progress_result is None:
                raise RuntimeError("Worker lost task ownership during progress update.")
            result = self.execute_step(step=step, goal=goal, session_id=session_id)
            results.append(result)
            if not result["success"]:
                error = result.get("error", "Execution step failed.")
                if worker_owned:
                    return {"success": False, "task_id": resolved_task_id, "agent": agent_name, "goal": goal, "plan": plan, "results": results, "error": error, "worker_owned": True}
                tasks.fail(resolved_task_id, error)
                return {"success": False, "task_id": resolved_task_id, "agent": agent_name, "goal": goal, "plan": plan, "results": results, "error": error}
        verification = self.verify(goal=goal, results=results)
        final_result = self.summarize(goal=goal, results=results, verification=verification)
        if not worker_owned:
            if verification["success"]:
                tasks.complete(resolved_task_id, final_result)
            else:
                tasks.fail(resolved_task_id, verification["reason"])
        response: dict[str, Any] = {"success": verification["success"], "task_id": resolved_task_id, "agent": agent_name, "goal": goal, "plan": plan, "results": results, "verification": verification, "final": final_result}
        if worker_owned:
            response["worker_owned"] = True
        return response

    def plan(self, goal: str, agent_name: str) -> list[dict[str, str]]:
        del goal
        if not agents.get(agent_name):
            agent_name = "general"
        if agent_name == "research":
            return [{"type": "think", "description": "Understand the research objective."}, {"type": "research", "description": "Identify the information required."}, {"type": "synthesize", "description": "Synthesize findings into a useful answer."}]
        if agent_name == "business":
            return [{"type": "think", "description": "Understand the business objective."}, {"type": "strategy", "description": "Develop a practical business strategy."}, {"type": "action", "description": "Define concrete execution steps."}]
        if agent_name == "creative":
            return [{"type": "think", "description": "Understand the creative objective."}, {"type": "create", "description": "Develop the creative solution."}, {"type": "refine", "description": "Refine the result for quality and impact."}]
        return [{"type": "think", "description": "Understand the user's objective."}, {"type": "action", "description": "Determine and execute the best next action."}, {"type": "verify", "description": "Verify that the objective was addressed."}]

    def execute_step(self, step: dict[str, str], goal: str, session_id: str | None = None) -> dict[str, Any]:
        del session_id
        step_type = step.get("type", "think")
        description = step.get("description", "")
        instructions = {
            "think": "You are the planning component of SAGE ONE. Analyze the goal and determine the most useful course of action.",
            "action": "You are SAGE ONE's execution planner. Give concrete, practical actions. Do not claim actions were performed unless a real tool performed them.",
            "research": "You are SAGE ONE's research planning component. Identify what information must be researched and what evidence would be useful. Do not fabricate research.",
            "synthesize": "You are SAGE ONE's synthesis component. Turn available reasoning into a clear useful result.",
            "strategy": "You are SAGE ONE's business strategy engine. Think practically about value, revenue, risk, resources and execution.",
            "create": "You are SAGE ONE's creative engine. Create the strongest practical solution for the user's objective.",
            "refine": "You are SAGE ONE's quality-control engine. Look for weaknesses and improve the proposed result.",
            "verify": "You are SAGE ONE's verification engine. Determine whether the objective has actually been addressed.",
        }
        instruction = instructions.get(step_type)
        if instruction is None:
            return {"success": False, "type": step_type, "error": f"Unknown execution step: {step_type}"}
        try:
            result = sage.router.think(system_instruction=instruction, user_message=f"GOAL:\n{goal}\n\nSTEP:\n{description}")
            return {"success": True, "type": step_type, "response": result.response, "provider": result.provider, "model": result.model}
        except Exception as error:
            return {"success": False, "type": step_type, "error": str(error)}

    def verify(self, goal: str, results: list[dict[str, Any]]) -> dict[str, Any]:
        del goal
        if not results:
            return {"success": False, "reason": "No execution results were produced."}
        if any(not result.get("success") for result in results):
            return {"success": False, "reason": "One or more execution steps failed."}
        return {"success": True, "reason": "All planned execution steps completed."}

    def summarize(self, goal: str, results: list[dict[str, Any]], verification: dict[str, Any]) -> str:
        if not verification["success"]:
            return "SAGE could not complete the goal. " + verification["reason"]
        responses = [result["response"] for result in results if result.get("response")]
        if not responses:
            return "The execution cycle completed, but no textual result was produced."
        combined = "\n\n".join(responses)
        try:
            final = sage.router.think(system_instruction="You are SAGE ONE. Produce the final answer from the execution results. Be direct and practical. Do not claim actions occurred unless the results prove they did.", user_message=f"ORIGINAL GOAL:\n{goal}\n\nEXECUTION RESULTS:\n{combined}")
            return final.response
        except Exception:
            return combined

    def status(self) -> dict[str, Any]:
        return {"name": self.name, "status": "operational", "max_steps": self.max_steps, "timestamp": datetime.now(timezone.utc).isoformat()}


orchestrator = SageOrchestrator()
