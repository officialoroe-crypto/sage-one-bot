import json
import os
from typing import Any

from cerebras.cloud.sdk import Cerebras

from config.settings import settings

from brain.providers import (
    BaseProvider,
    ProviderResult,
)


class CerebrasProvider(BaseProvider):
    name = "cerebras"

    def __init__(self):
        self.api_key = (
            settings.CEREBRAS_API_KEY
            or os.getenv("CEREBRAS_API_KEY")
        )

        self.model = (
            settings.CEREBRAS_MODEL
            or os.getenv(
                "CEREBRAS_MODEL",
                "gpt-oss-120b",
            )
        )

        self.client = None

        if self.api_key:
            self.client = Cerebras(
                api_key=self.api_key,
            )

    def available(self) -> bool:
        return self.client is not None

    def _build_messages(
        self,
        system_instruction: str,
        user_message: str,
        conversation: list[dict] | None = None,
    ) -> list[dict[str, Any]]:

        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": system_instruction,
            }
        ]

        if conversation:
            for message in conversation:
                role = message.get("role")
                content = message.get("content")

                if role in {
                    "system",
                    "user",
                    "assistant",
                } and content:
                    messages.append(
                        {
                            "role": role,
                            "content": str(content),
                        }
                    )

        messages.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        return messages

    def think(
        self,
        system_instruction: str,
        user_message: str,
        conversation: list[dict] | None = None,
    ) -> ProviderResult:

        if not self.client:
            raise RuntimeError(
                "CEREBRAS_API_KEY is not configured."
            )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(
                system_instruction,
                user_message,
                conversation,
            ),
            max_completion_tokens=4096,
        )

        content = (
            response.choices[0]
            .message
            .content
        )

        if not content:
            raise RuntimeError(
                "Cerebras returned an empty response."
            )

        return ProviderResult(
            provider=self.name,
            model=self.model,
            response=content,
            interaction_id=getattr(
                response,
                "id",
                None,
            ),
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
            raise RuntimeError(
                "CEREBRAS_API_KEY is not configured."
            )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(
                system_instruction,
                user_message,
                conversation,
            ),
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

        content = (
            response.choices[0]
            .message
            .content
        )

        if not content:
            raise RuntimeError(
                "Cerebras structured output returned empty content."
            )

        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Cerebras returned invalid JSON: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise RuntimeError(
                "Cerebras structured output must be a JSON object."
            )

        return ProviderResult(
            provider=self.name,
            model=self.model,
            response=content,
            interaction_id=getattr(
                response,
                "id",
                None,
            ),
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
            raise RuntimeError(
                "CEREBRAS_API_KEY is not configured."
            )

        messages = self._build_messages(
            system_instruction,
            user_message,
            conversation,
        )

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

                if not content:
                    raise RuntimeError(
                        "Cerebras returned an empty final response."
                    )

                return ProviderResult(
                    provider=self.name,
                    model=self.model,
                    response=content,
                    interaction_id=getattr(
                        response,
                        "id",
                        None,
                    ),
                )

            assistant_message = {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [],
            }

            for tool_call in tool_calls:
                assistant_message["tool_calls"].append(
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        },
                    }
                )

            messages.append(assistant_message)

            for tool_call in tool_calls:

                tool_name = tool_call.function.name
                raw_arguments = tool_call.function.arguments

                try:
                    arguments = json.loads(
                        raw_arguments or "{}"
                    )

                    tool_result = tool_executor(
                        tool_name,
                        arguments,
                    )

                except Exception as exc:
                    tool_result = {
                        "success": False,
                        "error": str(exc),
                    }

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": json.dumps(
                            tool_result,
                            default=str,
                        ),
                    }
                )

        raise RuntimeError(
            "Cerebras reached the maximum tool iterations."
        )


cerebras = CerebrasProvider()