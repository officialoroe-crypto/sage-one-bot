import time
from typing import Any

from brain.providers import ProviderResult
from brain.providers.cerebras_provider import CerebrasProvider
from brain.providers.groq_provider import GroqProvider
from brain.providers.gemini_provider import GeminiProvider
from brain.providers.ollama_provider import OllamaProvider
from brain.provider_resilience import classify_error, cooldown_for, record_telemetry
from brain.routing_policy import decide_routing
from config.settings import settings
from execution.resource import resource_guard


class BrainRouter:
    """Route SAGE inference without allowing heavy work onto the laptop."""

    def __init__(self):
        self.providers = [
            GroqProvider(),
            CerebrasProvider(),
            GeminiProvider(),
            OllamaProvider(),
        ]
        self.provider_by_name = {
            provider.name: provider
            for provider in self.providers
        }
        self.provider_health = {
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
            for provider in self.providers
        }

    def _is_in_cooldown(self, provider_name: str) -> bool:
        return time.time() < self.provider_health[provider_name]["cooldown_until"]

    def _mark_success(self, provider_name: str, structured: bool = False):
        health = self.provider_health[provider_name]
        health["successes"] += 1
        if structured:
            health["structured_successes"] += 1
        health["last_used"] = time.time()
        health["last_error"] = None
        health["last_error_class"] = None
        health["cooldown_until"] = 0.0

    def _mark_failure(
        self,
        provider_name: str,
        error: Exception,
        *,
        structured: bool = False,
        error_class: str | None = None,
    ):
        error_class = error_class or classify_error(error)
        health = self.provider_health[provider_name]
        health["failures"] += 1
        if structured:
            health["structured_failures"] += 1
        if error_class == "quota":
            health["quota_failures"] += 1
        if error_class in {"quota", "transient", "output", "unknown"}:
            health["retryable_failures"] += 1
        health["last_error"] = str(error)
        health["last_error_class"] = error_class
        health["last_failure_at"] = time.time()
        health["cooldown_until"] = time.time() + cooldown_for(error_class)
        return error_class

    def _validate_text(self, result: ProviderResult) -> ProviderResult:
        if not result.response or not result.response.strip():
            raise RuntimeError(f"{result.provider} returned empty response.")
        return result

    def _validate_structured(self, result: ProviderResult, schema: dict) -> ProviderResult:
        if not result.structured:
            raise RuntimeError(f"{result.provider} did not return structured output.")
        if not isinstance(result.data, dict):
            raise RuntimeError(f"{result.provider} structured output is not an object.")
        missing = [field for field in schema.get("required", []) if field not in result.data]
        if missing:
            raise RuntimeError(
                f"{result.provider} structured output is missing required fields: {missing}"
            )
        return result

    def _provider_order(self, description: str):
        snapshot = resource_guard.snapshot()
        return decide_routing(
            description=description,
            snapshot=snapshot,
            mode=settings.ROUTING_MODE,
            prefer_local=settings.PREFER_LOCAL,
        )

    def _iter_candidates(self, description: str):
        decision = self._provider_order(description)
        for provider_name in decision.provider_order:
            provider = self.provider_by_name[provider_name]
            if not provider.available():
                continue
            if self._is_in_cooldown(provider.name):
                continue
            yield provider

    def _record_success(self, provider: Any, operation: str, started: float, fallback_index: int, structured: bool):
        self._mark_success(provider.name, structured=structured)
        record_telemetry(
            provider=provider.name,
            model=getattr(provider, "model", None),
            operation=operation,
            outcome="success",
            duration_ms=(time.perf_counter() - started) * 1000,
            fallback_index=fallback_index,
            structured=structured,
        )

    def _record_failure(
        self,
        provider: Any,
        operation: str,
        started: float,
        fallback_index: int,
        error: Exception,
        *,
        structured: bool,
    ):
        error_class = self._mark_failure(
            provider.name,
            error,
            structured=structured,
        )
        record_telemetry(
            provider=provider.name,
            model=getattr(provider, "model", None),
            operation=operation,
            outcome="failure",
            duration_ms=(time.perf_counter() - started) * 1000,
            fallback_index=fallback_index,
            structured=structured,
            error_class=error_class,
            error=error,
        )
        return error_class

    def think(self, system_instruction: str, user_message: str, conversation: list[dict] | None = None) -> ProviderResult:
        errors = []
        for fallback_index, provider in enumerate(self._iter_candidates(user_message)):
            started = time.perf_counter()
            try:
                result = self._validate_text(
                    provider.think(
                        system_instruction=system_instruction,
                        user_message=user_message,
                        conversation=conversation,
                    )
                )
                self._record_success(provider, "think", started, fallback_index, False)
                return result
            except Exception as error:
                self._record_failure(
                    provider,
                    "think",
                    started,
                    fallback_index,
                    error,
                    structured=False,
                )
                errors.append(f"{provider.name}: {error}")
        raise RuntimeError("All allowed SAGE providers failed.\n" + "\n".join(errors))

    def think_structured(
        self,
        system_instruction: str,
        user_message: str,
        schema: dict,
        schema_name: str,
        conversation: list[dict] | None = None,
    ) -> ProviderResult:
        errors = []
        for fallback_index, provider in enumerate(self._iter_candidates(user_message)):
            started = time.perf_counter()
            try:
                result = self._validate_structured(
                    provider.think_structured(
                        system_instruction=system_instruction,
                        user_message=user_message,
                        schema=schema,
                        schema_name=schema_name,
                        conversation=conversation,
                    ),
                    schema,
                )
                self._record_success(provider, "think_structured", started, fallback_index, True)
                return result
            except NotImplementedError:
                record_telemetry(
                    provider=provider.name,
                    model=getattr(provider, "model", None),
                    operation="think_structured",
                    outcome="unsupported",
                    duration_ms=(time.perf_counter() - started) * 1000,
                    fallback_index=fallback_index,
                    structured=True,
                )
                errors.append(f"{provider.name}: structured output not implemented")
            except Exception as error:
                self._record_failure(
                    provider,
                    "think_structured",
                    started,
                    fallback_index,
                    error,
                    structured=True,
                )
                errors.append(f"{provider.name}: {error}")
        raise RuntimeError("All allowed structured-output providers failed.\n" + "\n".join(errors))

    def think_with_tools(
        self,
        system_instruction: str,
        user_message: str,
        tools: list[dict],
        tool_executor,
        conversation: list[dict] | None = None,
        max_iterations: int = 8,
    ) -> ProviderResult:
        errors = []
        for fallback_index, provider in enumerate(self._iter_candidates(user_message)):
            started = time.perf_counter()
            try:
                result = self._validate_text(
                    provider.think_with_tools(
                        system_instruction=system_instruction,
                        user_message=user_message,
                        tools=tools,
                        tool_executor=tool_executor,
                        conversation=conversation,
                        max_iterations=max_iterations,
                    )
                )
                self._record_success(provider, "think_with_tools", started, fallback_index, False)
                return result
            except NotImplementedError:
                record_telemetry(
                    provider=provider.name,
                    model=getattr(provider, "model", None),
                    operation="think_with_tools",
                    outcome="unsupported",
                    duration_ms=(time.perf_counter() - started) * 1000,
                    fallback_index=fallback_index,
                )
                errors.append(f"{provider.name}: tool calling not implemented")
            except Exception as error:
                self._record_failure(
                    provider,
                    "think_with_tools",
                    started,
                    fallback_index,
                    error,
                    structured=False,
                )
                errors.append(f"{provider.name}: {error}")
        raise RuntimeError("All allowed tool-capable providers failed.\n" + "\n".join(errors))

    def health(self) -> dict[str, Any]:
        result = {}
        now = time.time()
        for provider_name, health in self.provider_health.items():
            result[provider_name] = {
                "available": self.provider_by_name[provider_name].available(),
                "successes": health["successes"],
                "failures": health["failures"],
                "structured_successes": health["structured_successes"],
                "structured_failures": health["structured_failures"],
                "quota_failures": health["quota_failures"],
                "retryable_failures": health["retryable_failures"],
                "last_error": health["last_error"],
                "last_error_class": health["last_error_class"],
                "last_used": health["last_used"],
                "last_failure_at": health["last_failure_at"],
                "in_cooldown": now < health["cooldown_until"],
                "cooldown_remaining_seconds": max(
                    0.0,
                    round(health["cooldown_until"] - now, 2),
                ),
            }
        return result

    def routing(self, description: str) -> dict[str, Any]:
        snapshot = resource_guard.snapshot()
        decision = decide_routing(
            description=description,
            snapshot=snapshot,
            mode=settings.ROUTING_MODE,
            prefer_local=settings.PREFER_LOCAL,
        )
        return {
            "task_class": decision.task_class.value,
            "mode": decision.mode.value,
            "provider_order": list(decision.provider_order),
            "local_allowed": decision.local_allowed,
            "reason": decision.reason,
            "resource": {
                "cpu_percent": snapshot.cpu_percent,
                "memory_percent": snapshot.memory_percent,
                "resource_band": snapshot.band.value,
            },
        }


router = BrainRouter()
