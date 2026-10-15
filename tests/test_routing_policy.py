from execution.policy import TaskClass
from execution.resource import ResourceSnapshot
from brain.routing_policy import RoutingMode, decide_routing


def snapshot(cpu: float) -> ResourceSnapshot:
    return ResourceSnapshot(
        cpu_percent=cpu,
        memory_percent=50.0,
        cpu_count=2,
        timestamp=0.0,
    )


def test_heavy_tasks_are_cloud_only():
    decision = decide_routing(
        "deep research on competitors and verify sources",
        snapshot(20.0),
    )
    assert decision.task_class is TaskClass.HEAVY
    assert decision.provider_order == ("groq", "cerebras", "gemini")
    assert not decision.local_allowed


def test_medium_tasks_do_not_fall_back_to_ollama():
    decision = decide_routing(
        "search the web and compare several sources",
        snapshot(20.0),
    )
    assert decision.task_class is TaskClass.MEDIUM
    assert decision.provider_order == ("groq", "cerebras", "gemini")
    assert not decision.local_allowed


def test_light_auto_mode_is_cloud_first_when_cpu_is_safe():
    decision = decide_routing("say hello", snapshot(20.0))
    assert decision.task_class is TaskClass.LIGHT
    assert decision.provider_order == ("groq", "cerebras", "gemini", "ollama")
    assert decision.local_allowed


def test_busy_cpu_removes_ollama_from_auto_route():
    decision = decide_routing("say hello", snapshot(75.0))
    assert decision.provider_order == ("groq", "cerebras", "gemini")
    assert not decision.local_allowed


def test_explicit_local_mode_requires_light_work_and_safe_cpu():
    light = decide_routing("say hello", snapshot(20.0), mode="local")
    heavy = decide_routing("deep research", snapshot(20.0), mode="local")
    busy = decide_routing("say hello", snapshot(75.0), mode="local")

    assert light.mode is RoutingMode.LOCAL
    assert light.provider_order == ("ollama",)
    assert heavy.provider_order == ()
    assert busy.provider_order == ()


def test_explicit_cloud_mode_never_uses_local_provider():
    decision = decide_routing("say hello", snapshot(10.0), mode="cloud")
    assert decision.mode is RoutingMode.CLOUD
    assert decision.provider_order == ("groq", "cerebras", "gemini")
    assert not decision.local_allowed


def test_invalid_routing_mode_is_rejected():
    try:
        decide_routing("say hello", snapshot(10.0), mode="invalid")
    except ValueError as error:
        assert "Invalid routing mode" in str(error)
    else:
        raise AssertionError("invalid routing mode should raise")
