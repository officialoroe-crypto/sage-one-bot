from identity import api


def test_memory_review_endpoint_only_returns_unconfirmed_auto_learning(monkeypatch):
    monkeypatch.setattr(
        api,
        "_profile_from_claims",
        lambda _claims: {"id": "profile-owner"},
    )
    memories = [
        {
            "id": "pending-1",
            "profile_id": "profile-owner",
            "source": "auto_learning",
            "confirmed": False,
        },
        {
            "id": "confirmed-1",
            "profile_id": "profile-owner",
            "source": "auto_learning",
            "confirmed": True,
        },
        {
            "id": "manual-1",
            "profile_id": "profile-owner",
            "source": "user",
            "confirmed": False,
        },
        {
            "id": "other-profile-1",
            "profile_id": "profile-other",
            "source": "auto_learning",
            "confirmed": False,
        },
    ]
    monkeypatch.setattr(
        api,
        "list_memory",
        lambda profile_id, limit=100: [
            item for item in memories if item["profile_id"] == profile_id
        ],
    )

    result = api.get_profile_memory_review(
        {"auth_provider": "developer", "auth_subject": "owner"}
    )

    assert result["success"] is True
    assert result["count"] == 1
    assert [item["id"] for item in result["memories"]] == ["pending-1"]


def test_memory_review_endpoint_is_registered():
    routes = {
        (route.path, tuple(sorted(route.methods or [])))
        for route in api.router.routes
    }
    assert ("/identity/memory/review", ("GET",)) in routes
