from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shlex


@dataclass(frozen=True)
class AgentPolicy:
    """Safety policy for the SAGE development agent."""

    workspace: Path
    auto_write: bool = False
    allow_tests: bool = True

    writable_roots: tuple[str, ...] = (
        "app", "agents", "brain", "config", "database", "dev_agent",
        "execution", "memory", "missions", "permissions", "projects",
        "research", "tasks", "tools", "web", "tests", "docs", ".github",
    )

    forbidden_names: tuple[str, ...] = (
        ".env", ".env.local", ".env.production", "credentials.json",
    )

    def resolve(self, relative_path: str) -> Path:
        candidate = (self.workspace / relative_path).resolve()
        workspace = self.workspace.resolve()
        try:
            candidate.relative_to(workspace)
        except ValueError as exc:
            raise PermissionError("Path escapes the SAGE workspace.") from exc
        return candidate

    def _is_forbidden(self, relative_path: str) -> bool:
        path = relative_path.replace("\\", "/").lstrip("/")
        if not path or path == ".git" or path.startswith(".git/"):
            return True
        name = Path(path).name.lower()
        return name in {item.lower() for item in self.forbidden_names}

    def can_read(self, relative_path: str) -> bool:
        return not self._is_forbidden(relative_path)

    def assert_read_allowed(self, relative_path: str) -> None:
        if not self.can_read(relative_path):
            raise PermissionError(f"Reading '{relative_path}' is not permitted by the agent policy.")

    def can_write(self, relative_path: str) -> bool:
        path = relative_path.replace("\\", "/").lstrip("/")
        if self._is_forbidden(path):
            return False
        return any(path == root or path.startswith(root + "/") for root in self.writable_roots)

    def assert_write_allowed(self, relative_path: str) -> None:
        if not self.can_write(relative_path):
            raise PermissionError(f"Writing '{relative_path}' is not permitted by the agent policy.")

    def validate_check_command(self, command: str) -> list[str]:
        parts = shlex.split(command, posix=False)
        if not parts:
            raise PermissionError("Empty development command is not allowed.")

        normalized = command.lower().replace("\\", "/").strip()
        executable = parts[0].lower().replace(".exe", "")

        if executable == "pytest":
            return parts

        if executable in {"python", "py"}:
            if len(parts) >= 3 and parts[1] == "-m" and parts[2].lower() == "py_compile":
                return parts
            raise PermissionError("Python execution is restricted to py_compile checks.")

        if executable == "git":
            allowed_prefixes = (
                "git status",
                "git diff",
                "git log",
            )
            if normalized.startswith(allowed_prefixes):
                return parts
            raise PermissionError("Git execution is restricted to read-only status/diff/log checks.")

        raise PermissionError("Only approved non-destructive development checks are allowed.")
