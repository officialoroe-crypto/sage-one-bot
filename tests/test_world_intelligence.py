from world_intelligence.engine import DEFAULT_TOPICS, world_intelligence
from permissions.engine import permissions


def test_world_intelligence_permissions_are_bounded():
    assert permissions.get_permissions()["world.read"] is True
    assert permissions.get_permissions()["world.observe"] is True
    assert permissions.get_permissions()["world.learn"] is True
    assert permissions.get_permissions()["world.propose_upgrade"] is True
    assert permissions.get_permissions().get("security.modify") is False


def test_world_intelligence_status_is_not_self_modifying():
    status = world_intelligence.status()

    assert status["success"] is True
    assert status["public_sources_only"] is True
    assert status["self_modification"] is False
    assert status["upgrade_proposals_require_human_review"] is True
    assert status["default_topics"] == list(DEFAULT_TOPICS)


def test_world_upgrade_proposal_requires_review():
    result = world_intelligence.propose_upgrade(
        title="Test capability",
        reason="A repeated public-world pattern suggests a missing capability.",
        benefit="Could improve user execution if validated and approved.",
        evidence=["source:test"],
    )

    assert result["success"] is True
    assert result["proposal"]["status"] == "proposed"
    assert result["proposal"]["evidence"] == ["source:test"]

    proposals = world_intelligence.list_upgrade_proposals(limit=10)
    assert any(item["id"] == result["proposal"]["id"] for item in proposals)


def test_world_refresh_api_queues_durable_worker_task(monkeypatch):
    from world_intelligence import api

    created = {}

    class FakeTasks:
        def list(self):
            return []

        def create(self, **kwargs):
            created.update(kwargs)
            return {"id": "task-world-test", **kwargs}

    monkeypatch.setattr(api, "tasks", FakeTasks())
    response = api.world_refresh(
        api.WorldRefreshRequest(topics=["AI"]), claims={"owner_mode": True}
    )

    assert response["success"] is True
    assert response["status"] == "queued"
    assert response["task"]["agent"] == "world"
    assert created["priority"] == 4


def test_world_mutations_reject_non_owner_claims():
    import pytest
    from fastapi import HTTPException
    from world_intelligence import api

    with pytest.raises(HTTPException) as refresh_error:
        api.world_refresh(
            api.WorldRefreshRequest(topics=["AI"]), claims={"owner_mode": False}
        )
    assert refresh_error.value.status_code == 403

    with pytest.raises(HTTPException) as proposal_error:
        api.create_upgrade_proposal(
            api.UpgradeProposalRequest(
                title="Test", reason="Test reason", benefit="Test benefit"
            ),
            claims={"owner_mode": False},
        )
    assert proposal_error.value.status_code == 403
