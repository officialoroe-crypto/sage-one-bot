from missions.intelligence import MissionIntelligence


def test_recovery_strategy_is_deterministic_and_retry_first():
    intelligence = MissionIntelligence()

    task = {
        "id": "task-1",
        "agent": "general",
        "retries": 1,
        "max_retries": 3,
    }

    result = intelligence.recovery_strategy(task, "provider timeout")

    assert result["strategy"] == "retry"
    assert result["retryable"] is True
    assert result["retries"] == 1
    assert result["max_retries"] == 3


def test_recovery_strategy_escalates_exhausted_general_task():
    intelligence = MissionIntelligence()

    task = {
        "id": "task-2",
        "agent": "general",
        "retries": 3,
        "max_retries": 3,
    }

    result = intelligence.recovery_strategy(task, "repeated failure")

    assert result["strategy"] == "escalate"
    assert result["retryable"] is False


def test_recovery_strategy_research_has_specialized_fallback():
    intelligence = MissionIntelligence()

    task = {
        "id": "task-3",
        "agent": "research",
        "retries": 3,
        "max_retries": 3,
    }

    result = intelligence.recovery_strategy(task, "source fetch failed")

    assert result["strategy"] == "research_retry_with_fresh_context"
    assert result["retryable"] is True


def test_fallback_synthesis_uses_only_verified_results():
    intelligence = MissionIntelligence()
    tasks = [
        {
            "id": "a",
            "title": "Verified A",
            "agent": "general",
            "status": "completed",
            "verification_status": "verified",
            "result": "A result",
        },
        {
            "id": "b",
            "title": "Unverified B",
            "agent": "general",
            "status": "completed",
            "verification_status": "pending",
            "result": "B result",
        },
        {
            "id": "c",
            "title": "Failed C",
            "agent": "general",
            "status": "failed",
            "verification_status": "pending",
            "result": None,
        },
    ]

    result = intelligence._fallback(tasks, [tasks[2]])

    assert result["key_results"] == [
        {"task_id": "a", "title": "Verified A", "result": "A result"}
    ]
    assert result["confidence"] == "partial"
    assert "Failed C" in result["next_actions"][0]
