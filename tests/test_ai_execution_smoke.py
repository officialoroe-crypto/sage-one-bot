from brain.router import BrainRouter
from brain.providers import BaseProvider, ProviderResult
from app.worker import SageWorker


class FakeProvider(BaseProvider):
    name = "groq"
    model = "fake-model"

    def available(self) -> bool:
        return True

    def think(self, system_instruction, user_message, conversation=None):
        return ProviderResult(
            provider=self.name,
            model=self.model,
            response="SAGE test response",
            interaction_id="fake-1",
        )

    def think_with_tools(
        self,
        system_instruction,
        user_message,
        tools,
        tool_executor,
        conversation=None,
        max_iterations=8,
    ):
        return self.think(system_instruction, user_message, conversation)


def test_brain_router_can_produce_a_real_provider_result(monkeypatch):
    router = BrainRouter()
    fake = FakeProvider()
    monkeypatch.setattr(router, "_iter_candidates", lambda _description: iter([fake]))

    result = router.think("You are SAGE.", "Say hello.")

    assert result.provider == "groq"
    assert result.model == "fake-model"
    assert result.response == "SAGE test response"
    assert result.interaction_id == "fake-1"


def test_worker_run_once_completes_a_queued_task(monkeypatch):
    worker = SageWorker(worker_id="smoke-worker")
    queued = {
        "id": "task-smoke-1",
        "title": "Smoke task",
        "description": "Smoke task",
        "status": "running",
        "agent": "general",
        "priority": 3,
        "retries": 0,
    }
    completed = {**queued, "status": "completed", "result": "done"}

    monkeypatch.setattr(worker, "recover_expired_tasks", lambda: 0)
    monkeypatch.setattr(worker, "claim", lambda: queued)
    monkeypatch.setattr(worker, "execute_task", lambda task: {"success": True, "result": "done"})
    monkeypatch.setattr("app.worker.tasks.complete_claim", lambda **kwargs: completed)
    monkeypatch.setattr("app.worker.create_task_notification", lambda *args, **kwargs: None)

    result = worker.run_once()

    assert result["success"] is True
    assert result["task"]["status"] == "completed"
    assert result["task"]["result"] == "done"
