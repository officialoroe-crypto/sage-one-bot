from execution.engine import ExecutionEngine


class EventStore:
    def __init__(self):
        self.events = []

    def emit(self, **kwargs):
        self.events.append(kwargs)
        return "event-1"


def test_outcome_event_is_task_level_not_action_level():
    engine = ExecutionEngine()
    store = EventStore()

    engine.current_action_id = "action-last-tool"
    engine.current_session_id = "session-1"
    engine.current_mission_id = "mission-1"
    engine._get_task = lambda task_id: {"id": task_id, "title": "Goal"}

    import events.service

    original = events.service.event_store
    events.service.event_store = store
    try:
        engine._emit_outcome_event(
            "task-1",
            {
                "passed": True,
                "status": "passed",
                "evidence": "verified",
            },
        )
    finally:
        events.service.event_store = original

    assert store.events[0]["event_type"] == "OutcomeVerificationCompleted"
    assert store.events[0]["action_id"] is None
    assert store.events[0]["task_id"] == "task-1"
    assert store.events[0]["mission_id"] == "mission-1"
