from __future__ import annotations

from pathlib import Path
import subprocess

from dev_agent.policy import AgentPolicy


class WorkspaceTools:
    """Local repository tools exposed to the development agent."""

    def __init__(self, workspace: str | Path, policy: AgentPolicy | None = None):
        self.workspace = Path(workspace).resolve()
        self.policy = policy or AgentPolicy(self.workspace)

    def list_tree(self, path: str = ".", max_entries: int = 300) -> dict:
        root = self.policy.resolve(path)
        if not root.exists():
            return {"success": False, "error": f"Path does not exist: {path}"}
        entries = []
        for item in sorted(root.rglob("*")):
            if ".git" in item.parts or "__pycache__" in item.parts:
                continue
            entries.append(str(item.relative_to(self.workspace)).replace("\\", "/"))
            if len(entries) >= max_entries:
                break
        return {"success": True, "entries": entries, "truncated": len(entries) >= max_entries}

    def read_file(self, path: str, max_chars: int = 50000) -> dict:
        self.policy.assert_read_allowed(path)
        target = self.policy.resolve(path)
        if not target.is_file():
            return {"success": False, "error": f"File does not exist: {path}"}
        text = target.read_text(encoding="utf-8")
        return {"success": True, "path": path, "content": text[:max_chars], "truncated": len(text) > max_chars}

    def write_file(self, path: str, content: str) -> dict:
        self.policy.assert_write_allowed(path)
        if not self.policy.auto_write:
            return {"success": False, "approval_required": True, "error": "File writes require --apply."}
        target = self.policy.resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"success": True, "path": path, "bytes": len(content.encode("utf-8"))}

    def run_check(self, command: str, timeout: int = 120) -> dict:
        if not self.policy.allow_tests:
            return {"success": False, "error": "Test execution is disabled by policy."}
        try:
            parts = self.policy.validate_check_command(command)
            completed = subprocess.run(
                parts,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except (PermissionError, subprocess.TimeoutExpired, OSError) as exc:
            return {"success": False, "error": str(exc)}
        return {
            "success": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": completed.stdout[-12000:],
            "stderr": completed.stderr[-12000:],
        }

    def git_status(self) -> dict:
        return self.run_check("git status --short")

    def git_diff(self) -> dict:
        return self.run_check("git diff -- . ':!.env*'")
