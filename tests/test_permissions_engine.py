from permissions.engine import PermissionEngine


def test_unknown_permission_is_denied():
    engine = PermissionEngine()
    decision = engine.check("unknown.permission")
    assert decision.allowed is False
    assert "unknown permission" in decision.reason


def test_disabled_permission_is_denied():
    engine = PermissionEngine()
    engine.set_permission("web.read", False)
    decision = engine.check("web.read", risk="medium")
    assert decision.allowed is False
    assert "not granted" in decision.reason


def test_risk_ceiling_is_enforced():
    engine = PermissionEngine()
    engine.set_max_autonomous_risk("medium")
    decision = engine.check("automation.execute", risk="high")
    assert decision.allowed is False
    assert "exceeds" in decision.reason


def test_emergency_stop_blocks_non_control_operations_and_resume_restores_them():
    engine = PermissionEngine()
    engine.emergency_stop_now("test stop")

    blocked = engine.check("task.write", risk="medium")
    assert blocked.allowed is False
    assert blocked.emergency_stop is True

    engine.resume("test resume")
    allowed = engine.check("task.write", risk="medium")
    assert allowed.allowed is True


def test_owner_permission_change_is_recorded_in_audit():
    engine = PermissionEngine()
    engine.set_permission("web.read", True)
    audit = engine.audit()
    assert audit
    assert audit[-1]["source"] == "owner_control"
    assert audit[-1]["permission"] == "web.read"
