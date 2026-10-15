import time

from brain import provider_resilience
from brain.providers import ProviderResult
from brain.router import BrainRouter


class FakeProvider:
    def __init__(self, name, response=None, error=None):
        self.name = name
        self.model = f"{name}-model"
        self.response = response
        self.error = error

    def available(self):
        return True

    def think(self, **kwargs):
        if self.error:
            raise self.error
        return ProviderResult(
            provider=self.name,
            model=self.model,
            response=self.response or "ok",
        )

    def think_structured(self, **kwargs):
        return ProviderResult(
            provider=self.name,
            model=self.model,
            response='{"summary":"ok"}',
            structured=True,
            data={"summary": "ok"},
        )

    def think_with_tools(self, **kwargs):
        return self.think()


def test_error_classification_covers_quota_and_permanent_failures():
    assert provider_resilience.classify_error("HTTP 429 rate limit exceeded") == "quota"
    assert provider_resilience.classify_error("401 invalid API key") == "authentication"
    assert provider_resilience.classify_error("404 model not found") == "not_found"
    assert provider_resilience.classify_error("400 invalid request") == "invalid_request"
    assert provider_resilience.classify_error("connection timeout") == "transient"
    assert provider_resilience.classify_error("empty response") == "output"


def test_quota_failure_gets_longer_cooldown():
    router = BrainRouter()
    router.provider_health["groq"]["cooldown_until"] = 0

    error_class = router._mark_failure("groq", RuntimeError("429 quota exceeded"))

    assert error_class == "quota"
    assert router.provider_health["groq"]["quota_failures"] == 1
    assert router.provider_health["groq"]["cooldown_until"] >= time.time() + 119


def test_router_falls_back_after_transient_provider_failure(monkeypatch):
    router = BrainRouter()
    first = FakeProvider("first", error=RuntimeError("503 service unavailable"))
    second = FakeProvider("second", response="fallback worked")
    router.providers = [first, second]
    router.provider_by_name = {provider.name: provider for provider in router.providers}
    router.provider_health = {
        provider.name: {
            "successes": 0,
            "failures": 0,
            "structured_successes": 0,
            "structured_failures": 0,
            "quota_failures": 0,
            "retryable_failures": 0,
            "last_error": None,
            "last_error_class": None,
            "last_used": None,
            "last_failure_at": None,
            "cooldown_until": 0.0,
        }
        for provider in router.providers
    }
    monkeypatch.setattr(router, "_iter_candidates", lambda description: iter([first, second]))
    monkeypatch.setattr(provider_resilience, "record_telemetry", lambda **kwargs: None)

    result = router.think("system", "hello")

    assert result.provider == "second"
    assert router.provider_health["first"]["last_error_class"] == "transient"
    assert router.provider_health["second"]["successes"] == 1


def test_durable_telemetry_does_not_store_prompt_content(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy import text

    test_engine = create_engine(
        f"sqlite:///{tmp_path / 'telemetry.db'}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(provider_resilience, "engine", test_engine)

    provider_resilience.record_telemetry(
        provider="groq",
        model="test-model",
        operation="think",
        outcome="failure",
        duration_ms=12.3,
        error_class="quota",
        error="429 quota exceeded",
    )

    with test_engine.begin() as connection:
        row = connection.execute(
            text("SELECT provider, error, duration_ms FROM provider_telemetry")
        ).mappings().first()

    assert row["provider"] == "groq"
    assert row["error"] == "429 quota exceeded"
    assert row["duration_ms"] == 12.3
