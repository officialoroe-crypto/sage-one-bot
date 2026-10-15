from agentic.engine import AgenticActionEngine
from agentic.models import ActionRequest
from permissions.engine import PermissionEngine
from tools.registry import ToolRegistry


class FakeLogStore:
    def start(self, **kwargs):
        return kwargs["action_id"]

    def finish(self, **kwargs):
        return None


class FakeEventStore:
    def __init__(self):
        self.events = []

    def emit(self, **kwargs):
        self.events.append(kwargs)
        return f"event-{len(self.events)}"


def build_engine(handler):
    registry = ToolRegistry()
    registry.register(
        name="event_tool",
        description="Event test tool.",
        capability="test.execute",
        risk="low",
        permission="tool.execute",
        handler=handler,
        parameters={"properties": {"name": {"type": "string"}}},
    )
    events = FakeEventStore()
    engine = AgenticActionEngine(
        registry=registry,
        permission_engine=PermissionEngine(),
        log_store=FakeLogStore(),
        event_store=events,
    )
    return engine, events


def test_action_lifecycle_events_are_emitted_in_order():
    engine, events = build_engine(
        lambda name: {"success": True, "name": name}
    )

    result = engine.execute(
        ActionRequest(
            tool_name="event_tool",
            arguments={"name": "SAGE"},
            session_id="session-1",
            task_id="task-1",
            mission_id="mission-1",
            owner_authorized=True,
        )
    )

    assert result.success is True
    assert result.event_ids == ["event-1", "event-2", "event-3"]
    assert [event["event_type"] for event in events.events] == [
        "ActionStarted",
        "ActionCompleted",
        "VerificationCompleted",
    ]
    assert all(event["mission_id"] == "mission-1" for event in events.events)
    assert all(event["task_id"] == "task-1" for event in events.events)


def test_denied_action_emits_permission_denied_event():
    engine, events = build_engine(
        lambda name: {"success": True}
    )

    result = engine.execute(
        ActionRequest(
            tool_name="event_tool",
            arguments={"name": "SAGE"},
            owner_authorized=False,
        )
    )

    assert result.success is False
    assert [event["event_type"] for event in events.events] == [
        "ActionPermissionDenied"
    ]
