from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ProviderResult:
    provider: str
    model: str
    response: str
    interaction_id: Optional[str] = None
    structured: bool = False
    data: Optional[dict[str, Any]] = None


class BaseProvider:
    name = "base"

    def available(self) -> bool:
        raise NotImplementedError

    def think(
        self,
        system_instruction: str,
        user_message: str,
        conversation: list[dict] | None = None,
    ) -> ProviderResult:
        raise NotImplementedError

    def think_structured(
        self,
        system_instruction: str,
        user_message: str,
        schema: dict,
        schema_name: str,
        conversation: list[dict] | None = None,
    ) -> ProviderResult:
        raise NotImplementedError(
            f"Structured output is not implemented for provider: {self.name}"
        )

    def think_with_tools(
        self,
        system_instruction: str,
        user_message: str,
        tools: list[dict],
        tool_executor,
        conversation: list[dict] | None = None,
        max_iterations: int = 8,
    ) -> ProviderResult:
        raise NotImplementedError(
            f"Tool calling is not implemented for provider: {self.name}"
        )
