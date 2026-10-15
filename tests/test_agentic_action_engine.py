from dataclasses import dataclass
from typing import Any

from agentic.engine import AgenticActionEngine
from agentic.models import ActionRequest
from permissions.engine import PermissionEngine
from tools.registry import ToolRegistry


@dataclass
class FakeLog:
    action_id: str
    status: str
    error: str | None = None
    result: Any = None


class FakeLogStore:
    def __init__(self) -> None:
        self.rows: dict[str, FakeLog] = {}
        self.starts = 0
        self.finishes = 0
        self.evidence = []

    def start(self, **kwargs) -> str:
        self.starts += 1
        self.start_kwargs = kwargs
        action_id = kwargs["action_id"]
        self.rows[action_id] = FakeLog(action_id, "started")
        return action_id

    def record_evidence(self, **kwargs) -> str:
        self.evidence.append(kwargs)
        return f"evidence-{len(self.evidence)}"

    def finish(self, **kwargs) -> None:
        self.finishes += 1
        row = self.rows[kwargs["action_id"]]
        row.status = kwargs["status"]
        row.error = kwargs.get("error")
        row.result = kwargs.get("result")


def build_engine(handler, *, permission="tool.execute", risk="low"):
    registry = ToolRegistry()
    registry.register(
        name="demo_tool",
        description="Test tool.",
        capability="test.execute",
        risk=risk,
        permission=permission,
        handler=handler,
        parameters={
            "required": ["name"],
            "properties": {
                "name": {"type": "string"},
            },
        },
    )
    permissions = PermissionEngine()
    logs = FakeLogStore()
    return AgenticActionEngine(
        registry=registry,
        permission_engine=permissions,
        log_store=logs,
    ), logs


def test_allowed_action_executes_and_is_verified():
    calls = []

    def handler(name: str):
        calls.append(name)
        return {"success": True, "message": f"Hello {name}"}

    engine, logs = build_engine(handler)

    result = engine.execute(
        ActionRequest(
            tool_name="demo_tool",
            arguments={"name": "SAGE"},
            owner_authorized=True,
        )
    )

    assert result.success is True
    assert result.status == "completed"
    assert result.verification_status == "passed"
    assert result.result["message"] == "Hello SAGE"
    assert calls == ["SAGE"]
    assert logs.starts == 1
    assert logs.finishes == 1


def test_owner_authorization_is_fail_closed():
    calls = []

    def handler(name: str):
        calls.append(name)
        return {"success": True}

    engine, logs = build_engine(handler)

    result = engine.execute(
        ActionRequest(
            tool_name="demo_tool",
            arguments={"name": "SAGE"},
            owner_authorized=False,
        )
    )

    assert result.success is False
    assert result.status == "denied"
    assert "owner" in result.permission_reason.lower()
    assert calls == []
    assert logs.finishes == 1


def test_disabled_permission_denies_before_execution():
    calls = []

    def handler(name: str):
        calls.append(name)
        return {"success": True}

    engine, logs = build_engine(
        handler,
        permission="file.write",
        risk="low",
    )

    result = engine.execute(
        ActionRequest(
            tool_name="demo_tool",
            arguments={"name": "SAGE"},
            owner_authorized=True,
        )
    )

    assert result.success is False
    assert result.status == "denied"
    assert calls == []
    assert logs.finishes == 1


def test_risk_above_autonomous_limit_denies():
    calls = []

    def handler(name: str):
        calls.append(name)
        return {"success": True}

    engine, logs = build_engine(
        handler,
        permission="memory.write",
        risk="high",
    )

    result = engine.execute(
        ActionRequest(
            tool_name="demo_tool",
            arguments={"name": "SAGE"},
            owner_authorized=True,
        )
    )

    assert result.success is False
    assert result.status == "denied"
    assert "risk" in result.permission_reason.lower()
    assert calls == []
    assert logs.finishes == 1


def test_unknown_tool_is_denied_and_never_called():
    engine, logs = build_engine(lambda name: {"success": True})

    result = engine.execute(
        ActionRequest(
            tool_name="does_not_exist",
            arguments={},
            owner_authorized=True,
        )
    )

    assert result.success is False
    assert result.status == "denied"
    assert result.permission == "unknown"
    assert logs.finishes == 1


def test_invalid_arguments_are_rejected_before_handler():
    calls = []

    def handler(name: str):
        calls.append(name)
        return {"success": True}

    engine, logs = build_engine(handler)

    result = engine.execute(
        ActionRequest(
            tool_name="demo_tool",
            arguments={},
            owner_authorized=True,
        )
    )

    assert result.success is False
    assert result.status == "invalid_arguments"
    assert "required argument" in result.error.lower()
    assert calls == []
    assert logs.finishes == 1


def test_argument_type_is_validated():
    calls = []

    def handler(name: str):
        calls.append(name)
        return {"success": True}

    engine, logs = build_engine(handler)

    result = engine.execute(
        ActionRequest(
            tool_name="demo_tool",
            arguments={"name": 123},
            owner_authorized=True,
        )
    )

    assert result.success is False
    assert result.status == "invalid_arguments"
    assert "type string" in result.error.lower()
    assert calls == []
    assert logs.finishes == 1


def test_handler_exception_is_captured_and_logged():
    def handler(name: str):
        raise RuntimeError("boom")

    engine, logs = build_engine(handler)

    result = engine.execute(
        ActionRequest(
            tool_name="demo_tool",
            arguments={"name": "SAGE"},
            owner_authorized=True,
        )
    )

    assert result.success is False
    assert result.status == "failed"
    assert "RuntimeError: boom" in result.error
    assert result.verification_status == "failed"
    assert logs.rows[result.action_id].status == "failed"


def test_tool_reported_failure_is_not_marked_success():
    def handler(name: str):
        return {"success": False, "error": "not completed"}

    engine, logs = build_engine(handler)

    result = engine.execute(
        ActionRequest(
            tool_name="demo_tool",
            arguments={"name": "SAGE"},
            owner_authorized=True,
        )
    )

    assert result.success is False
    assert result.status == "failed"
    assert result.verification_status == "failed"
    assert "not completed" in result.error
    assert logs.rows[result.action_id].status == "failed"


def test_action_context_is_traceable_and_evidence_is_persisted():
    def handler(name: str):
        return {"success": True, "message": name}

    engine, logs = build_engine(handler)

    result = engine.execute(
        ActionRequest(
            tool_name="demo_tool",
            arguments={"name": "SAGE"},
            session_id="session-1",
            task_id="task-1",
            mission_id="mission-1",
            parent_action_id="action-parent",
            owner_authorized=True,
        )
    )

    assert result.success is True
    assert result.mission_id == "mission-1"
    assert result.parent_action_id == "action-parent"
    assert result.evidence
    assert result.evidence[0]["persisted"] is True
    assert logs.evidence[0]["mission_id"] == "mission-1"
    assert logs.evidence[0]["task_id"] == "task-1"
    assert logs.evidence[0]["parent_action_id"] == "action-parent"


def test_action_evidence_persistence_failure_fails_closed_after_execution():
    class BrokenEvidenceLog(FakeLogStore):
        def record_evidence(self, **kwargs) -> str:
            raise RuntimeError("evidence store unavailable")

    def handler(name: str):
        return {"success": True}

    registry = ToolRegistry()
    registry.register(
        name="demo_tool",
        description="Test tool.",
        capability="test.execute",
        risk="low",
        permission="tool.execute",
        handler=handler,
        parameters={"required": ["name"], "properties": {"name": {"type": "string"}}},
    )
    logs = BrokenEvidenceLog()
    engine = AgenticActionEngine(
        registry=registry,
        permission_engine=PermissionEngine(),
        log_store=logs,
    )

    result = engine.execute(
        ActionRequest(
            tool_name="demo_tool",
            arguments={"name": "SAGE"},
            owner_authorized=True,
        )
    )

    assert result.success is False
    assert "Evidence persistence failed" in result.error


def test_action_log_start_receives_full_correlation_context():
    engine, logs = build_engine(lambda name: {"success": True})

    result = engine.execute(
        ActionRequest(
            tool_name="demo_tool",
            arguments={"name": "SAGE"},
            session_id="session-1",
            task_id="task-1",
            mission_id="mission-1",
            parent_action_id="action-parent",
            source="mission_execution",
            owner_authorized=True,
        )
    )

    assert result.success is True
    request = logs.start_kwargs["request"]
    assert request.session_id == "session-1"
    assert request.task_id == "task-1"
    assert request.mission_id == "mission-1"
    assert request.parent_action_id == "action-parent"
    assert request.source == "mission_execution"
