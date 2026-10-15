import json
import os
from typing import Any, cast

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from brain.providers import BaseProvider, ProviderResult
from config.settings import settings


class GeminiProvider(BaseProvider):
    """Gemini through Google's OpenAI-compatible endpoint."""

    name = "gemini"

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        self.model = os.getenv("SAGE_GEMINI_MODEL", settings.MODEL)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        self.client = (
            OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=90.0,
                default_headers={"x-goog-api-client": "sage-one/0.1.0"},
            )
            if self.api_key
            else None
        )

    def available(self) -> bool:
        return self.client is not None

    def _messages(
        self,
        system_instruction: str,
        user_message: str,
        conversation: list[dict] | None = None,
    ) -> list[ChatCompletionMessageParam]:
        raw: list[dict[str, Any]] = [
            {"role": "system", "content": system_instruction}
        ]
        if conversation:
            raw.extend(conversation)
        raw.append({"role": "user", "content": user_message})
        return cast(list[ChatCompletionMessageParam], raw)

    def think(
        self,
        system_instruction: str,
        user_message: str,
        conversation: list[dict] | None = None,
    ) -> ProviderResult:
        if not self.client:
            raise RuntimeError("GEMINI_API_KEY is not configured.")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self._messages(system_instruction, user_message, conversation),
            max_completion_tokens=4096,
        )
        content = response.choices[0].message.content or ""
        if not content.strip():
            raise RuntimeError("Gemini returned an empty response.")
        return ProviderResult(
            provider=self.name,
            model=self.model,
            response=content,
            interaction_id=response.id,
        )

    def think_structured(
        self,
        system_instruction: str,
        user_message: str,
        schema: dict,
        schema_name: str,
        conversation: list[dict] | None = None,
    ) -> ProviderResult:
        if not self.client:
            raise RuntimeError("GEMINI_API_KEY is not configured.")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self._messages(system_instruction, user_message, conversation),
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                },
            },
            max_completion_tokens=4096,
        )
        content = response.choices[0].message.content or ""
        if not content.strip():
            raise RuntimeError("Gemini structured output returned empty content.")
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Gemini returned invalid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise RuntimeError("Gemini structured output must be a JSON object.")
        return ProviderResult(
            provider=self.name,
            model=self.model,
            response=content,
            interaction_id=response.id,
            structured=True,
            data=data,
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
        if not self.client:
            raise RuntimeError("GEMINI_API_KEY is not configured.")

        messages = self._messages(system_instruction, user_message, conversation)

        for _ in range(max_iterations):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_completion_tokens=4096,
            )
            message = response.choices[0].message
            tool_calls = message.tool_calls or []

            if not tool_calls:
                content = message.content or ""
                if not content.strip():
                    raise RuntimeError("Gemini returned an empty final response.")
                return ProviderResult(
                    provider=self.name,
                    model=self.model,
                    response=content,
                    interaction_id=response.id,
                )

            assistant_message: dict[str, Any] = {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [],
            }
            for call in tool_calls:
                assistant_message["tool_calls"].append(
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                )
            messages.append(cast(ChatCompletionMessageParam, assistant_message))

            for call in tool_calls:
                try:
                    arguments = json.loads(call.function.arguments or "{}")
                    result = tool_executor(call.function.name, arguments)
                except Exception as exc:
                    result = {"success": False, "error": str(exc)}
                messages.append(
                    cast(
                        ChatCompletionMessageParam,
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": json.dumps(result, default=str),
                        },
                    )
                )

        raise RuntimeError(
            f"Gemini reached the maximum of {max_iterations} tool iterations."
        )
