import json
import os
from typing import Any, cast

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from brain.providers import (
    BaseProvider,
    ProviderResult,
)


class OllamaProvider(BaseProvider):

    name = "ollama"

    def __init__(self):

        self.base_url = os.getenv(
            "OLLAMA_BASE_URL",
            "http://127.0.0.1:11434/v1",
        )

        self.model = os.getenv(
            "SAGE_OLLAMA_MODEL",
            "llama3.2:3b",
        )

        self.client = OpenAI(
            base_url=self.base_url,
            api_key="ollama",
            timeout=60.0,
        )

    def available(self) -> bool:

        try:

            models = self.client.models.list()

            for model in models.data:

                if model.id == self.model:
                    return True

            return False

        except Exception:

            return False

    def _build_messages(
        self,
        system_instruction: str,
        user_message: str,
        conversation: list[dict] | None = None,
    ):

        raw_messages = [
            {
                "role": "system",
                "content": system_instruction,
            }
        ]

        if conversation:
            raw_messages.extend(
                conversation
            )

        raw_messages.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        return cast(
            list[ChatCompletionMessageParam],
            raw_messages,
        )

    def think(
        self,
        system_instruction: str,
        user_message: str,
        conversation: list[dict] | None = None,
    ) -> ProviderResult:

        messages = self._build_messages(
            system_instruction,
            user_message,
            conversation,
        )

        completion = (
            self.client
            .chat
            .completions
            .create(
                model=self.model,
                messages=messages,
            )
        )

        response = (
            completion
            .choices[0]
            .message
            .content
        )

        if not response or not response.strip():
            raise RuntimeError(
                "Ollama returned an empty response."
            )

        return ProviderResult(
            provider=self.name,
            model=self.model,
            response=response,
            interaction_id=completion.id,
            structured=False,
        )

    def think_structured(
        self,
        system_instruction: str,
        user_message: str,
        schema: dict[str, Any],
        schema_name: str = "sage_response",
        conversation: list[dict] | None = None,
    ) -> ProviderResult:

        messages = self._build_messages(
            system_instruction,
            user_message,
            conversation,
        )

        # Ollama's OpenAI-compatible API supports
        # JSON response mode. The schema is also
        # placed into the system instruction so
        # smaller local models have explicit guidance.
        structured_instruction = (
            system_instruction
            + "\n\n"
            + "Return ONLY valid JSON. "
            + "Your JSON must conform to this schema:\n"
            + json.dumps(schema, indent=2)
        )

        messages = self._build_messages(
            structured_instruction,
            user_message,
            conversation,
        )

        completion = (
            self.client
            .chat
            .completions
            .create(
                model=self.model,
                messages=messages,
                response_format={
                    "type": "json_object"
                },
            )
        )

        response = (
            completion
            .choices[0]
            .message
            .content
        )

        if not response or not response.strip():
            raise RuntimeError(
                "Ollama returned an empty structured response."
            )

        try:
            parsed = json.loads(response)
        except json.JSONDecodeError as error:
            raise RuntimeError(
                f"Ollama returned invalid JSON: {error}"
            ) from error

        if not isinstance(parsed, dict):
            raise RuntimeError(
                "Ollama structured response "
                "must be a JSON object."
            )

        return ProviderResult(
            provider=self.name,
            model=self.model,
            response=response,
            interaction_id=completion.id,
            structured=True,
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
        """OpenAI-compatible tool loop (Ollama supports tools on tool-capable models)."""

        messages: list[Any] = list(
            self._build_messages(system_instruction, user_message, conversation)
        )

        for _ in range(max_iterations):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=cast(Any, messages),
                tools=cast(Any, tools),
                tool_choice="auto",
            )
            message = response.choices[0].message
            tool_calls = message.tool_calls or []

            if not tool_calls:
                content = message.content or ""
                if not content.strip():
                    raise RuntimeError("Ollama returned an empty final response.")
                return ProviderResult(
                    provider=self.name,
                    model=self.model,
                    response=content,
                    interaction_id=getattr(response, "id", None),
                )

            messages.append(
                {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.function.name,  # type: ignore[union-attr]
                                "arguments": call.function.arguments,  # type: ignore[union-attr]
                            },
                        }
                        for call in tool_calls
                    ],
                }
            )

            for call in tool_calls:
                name = call.function.name  # type: ignore[union-attr]
                try:
                    arguments = json.loads(call.function.arguments or "{}")  # type: ignore[union-attr]
                    tool_result = tool_executor(name, arguments)
                except Exception as exc:
                    tool_result = {"success": False, "error": str(exc)}
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": name,
                        "content": json.dumps(tool_result, default=str),
                    }
                )

        raise RuntimeError("Ollama reached the maximum tool iterations.")


ollama = OllamaProvider()