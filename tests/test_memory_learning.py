from identity import memory_learning


def test_memory_learning_requires_consent():
    result = memory_learning.learn_memory_candidates(
        profile_id="owner-1",
        memory_consent=False,
        candidates=[{"memory_type": "preference", "content": "Prefers concise answers"}],
    )

    assert result["success"] is False
    assert result["status"] == "consent_required"
    assert result["learned"] == []


def test_memory_learning_filters_duplicates_and_secrets(monkeypatch):
    stored = []
    monkeypatch.setattr(
        memory_learning,
        "list_memory",
        lambda profile_id, limit=1000: [
            {"content": "Prefers concise answers"},
        ],
    )

    def fake_add_memory(**kwargs):
        stored.append(kwargs)
        return {"id": "memory-1", **kwargs}

    monkeypatch.setattr(memory_learning, "add_memory", fake_add_memory)

    result = memory_learning.learn_memory_candidates(
        profile_id="owner-1",
        memory_consent=True,
        candidates=[
            {"memory_type": "preference", "content": "Prefers concise answers"},
            {"memory_type": "skill", "content": "Can edit video"},
            {"memory_type": "fact", "content": "api_key=do-not-store"},
        ],
    )

    assert result["success"] is True
    assert [item["content"] for item in result["learned"]] == ["Can edit video"]
    assert any(item["reason"] == "duplicate" for item in result["skipped"])
    assert any(item["reason"] == "secret_like_content" for item in result["rejected"])
    assert stored[0]["source"] == "auto_learning"
    assert stored[0]["confirmed"] is False


def test_memory_learning_rejects_unknown_types_and_invalid_values(monkeypatch):
    monkeypatch.setattr(memory_learning, "list_memory", lambda profile_id, limit=1000: [])
    monkeypatch.setattr(
        memory_learning,
        "add_memory",
        lambda **kwargs: {"id": "memory-1", **kwargs},
    )

    result = memory_learning.learn_memory_candidates(
        profile_id="owner-1",
        memory_consent=True,
        candidates=[
            {"memory_type": "unknown", "content": "x"},
            {"memory_type": "goal", "content": "y", "confidence": 2},
        ],
    )

    reasons = {item["reason"] for item in result["rejected"]}
    assert "unsupported_memory_type" in reasons
    assert "invalid_confidence" in reasons
    assert result["learned"] == []
