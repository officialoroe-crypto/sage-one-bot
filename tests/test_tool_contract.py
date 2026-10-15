import pytest

from tools.registry import ToolRegistry


def test_tool_contract_metadata_is_preserved():
    registry = ToolRegistry()
    registry.register(
        name="contract_tool",
        description="Contract test.",
        capability="test.contract",
        risk="low",
        permission="tool.execute",
        handler=lambda: {"success": True},
        parameters={"properties": {}},
        output_schema={"type": "object"},
        cost_policy={"spark": 2},
        timeout_seconds=5,
        retry_policy={"max_attempts": 2},
        verification_policy={"required": True},
        audit_policy={"required": True},
        side_effect_class="REVERSIBLE",
    )

    tool = registry.get("contract_tool")
    assert tool is not None
    assert tool.output_schema == {"type": "object"}
    assert tool.cost_policy == {"spark": 2}
    assert tool.timeout_seconds == 5
    assert tool.retry_policy["max_attempts"] == 2
    assert tool.verification_policy["required"] is True
    assert tool.audit_policy["required"] is True
    assert tool.side_effect_class == "REVERSIBLE"

    listed = registry.list()[0]
    assert listed["side_effect_class"] == "REVERSIBLE"


def test_invalid_side_effect_class_is_rejected():
    registry = ToolRegistry()

    with pytest.raises(ValueError):
        registry.register(
            name="invalid_tool",
            description="Invalid contract.",
            capability="test.contract",
            risk="low",
            permission="tool.execute",
            handler=lambda: {"success": True},
            side_effect_class="UNKNOWN",
        )


def test_invalid_timeout_is_rejected():
    registry = ToolRegistry()

    with pytest.raises(ValueError):
        registry.register(
            name="invalid_timeout",
            description="Invalid timeout.",
            capability="test.contract",
            risk="low",
            permission="tool.execute",
            handler=lambda: {"success": True},
            timeout_seconds=0,
        )
