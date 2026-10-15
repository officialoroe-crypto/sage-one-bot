from __future__ import annotations

import json
from typing import Any

from brain.router import router
from dev_agent.tools import WorkspaceTools


SYSTEM_PROMPT = """
You are SAGE ONE's Development Agent.

Your job is to implement software changes in the SAGE ONE repository safely and completely.
Inspect the repository before changing it. Prefer existing architecture and interfaces over
inventing parallel systems. Make coherent multi-file changes when required.

Rules:
- Capability does not equal permission.
- Never access, print, modify, or commit secrets such as .env files.
- Never run destructive shell commands, deployments, package publishing, or remote Git operations.
- Use repository tools to inspect and edit files.
- Use tests and static checks after changes.
- If a required operation is outside your tools or permission boundary, stop and report it.
- Do not claim success unless the requested work and its checks actually succeeded.
- Prefer complete, maintainable implementations over temporary patches.
- Preserve backward compatibility unless the task explicitly requires a break.
- At the end, summarize files changed, checks run, failures, and remaining work.
"""


class DevelopmentAgent:
    """Controlled autonomous coding loop for SAGE ONE."""

    def __init__(self, workspace: str, apply_changes: bool = False):
        self.tools = WorkspaceTools(workspace)
        self.tools.policy = type(self.tools.policy)(
            self.tools.workspace,
            auto_write=apply_changes,
            allow_tests=True,
        )

    def _tool_executor(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        mapping = {
            "list_tree": self.tools.list_tree,
            "read_file": self.tools.read_file,
            "write_file": self.tools.write_file,
            "run_check": self.tools.run_check,
            "git_status": self.tools.git_status,
            "git_diff": self.tools.git_diff,
        }
        tool = mapping.get(name)
        if tool is None:
            return {"success": False, "error": f"Unknown development tool: {name}"}
        try:
            return tool(**arguments)
        except PermissionError as exc:
            return {"success": False, "permission_denied": True, "error": str(exc)}
        except Exception as exc:
            return {"success": False, "error": f"Development tool failed: {exc}"}

    @staticmethod
    def tool_schema() -> list[dict[str, Any]]:
        return [
            {"type": "function", "function": {"name": "list_tree", "description": "List repository files.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "max_entries": {"type": "integer"}}, "required": []}}},
            {"type": "function", "function": {"name": "read_file", "description": "Read a UTF-8 repository file that is not protected by policy.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "max_chars": {"type": "integer"}}, "required": ["path"]}}},
            {"type": "function", "function": {"name": "write_file", "description": "Create or replace an approved repository source/test file. Requires --apply.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
            {"type": "function", "function": {"name": "run_check", "description": "Run an approved non-destructive development check.", "parameters": {"type": "object", "properties": {"command": {"type": "string"}, "timeout": {"type": "integer"}}, "required": ["command"]}}},
            {"type": "function", "function": {"name": "git_status", "description": "Show working tree status.", "parameters": {"type": "object", "properties": {}, "required": []}}},
            {"type": "function", "function": {"name": "git_diff", "description": "Show current source diff, excluding secrets.", "parameters": {"type": "object", "properties": {}, "required": []}}},
        ]

    def run(self, task: str, max_iterations: int = 12) -> dict[str, Any]:
        result = router.think_with_tools(
            system_instruction=SYSTEM_PROMPT,
            user_message=task,
            tools=self.tool_schema(),
            tool_executor=self._tool_executor,
            max_iterations=max_iterations,
        )
        response = (result.response or "").strip()
        success = bool(response) and bool(result.provider) and bool(result.model)
        return {
            "success": success,
            "response": response,
            "provider": result.provider,
            "model": result.model,
            "interaction_id": result.interaction_id,
        }

    def plan(self, task: str) -> dict[str, Any]:
        return self.run(
            "Create an implementation plan only. Do not write files.\n\nTASK:\n" + task
        )

    def apply(self, task: str) -> dict[str, Any]:
        self.tools.policy = type(self.tools.policy)(
            self.tools.workspace,
            auto_write=True,
            allow_tests=True,
        )
        return self.run(
            task + "\n\nImplement the task now. Inspect first, then make the complete changes and run appropriate static/unit checks. Do not push or commit."
        )

    def to_json(self, result: dict[str, Any]) -> str:
        return json.dumps(result, indent=2, default=str)
