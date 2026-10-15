import json
import os
from typing import Any

from groq import Groq

from config.settings import settings

from brain.providers import (
    BaseProvider,
    ProviderResult,
)


class GroqProvider(BaseProvider):
    name = "groq"

    def __init__(self):
        self.api_key = (
            settings.GROQ_API_KEY
            or os.getenv("GROQ_API_KEY")
        )

        self.model = (
            settings.GROQ_MODEL
            or os.getenv("SAGE_GROQ_MODEL")
            or "openai/gpt-oss-20b"
        )

        self.client = None

        if self.api_key:
            self.client = Groq(
                api_key=self.api_key,
                timeout=60.0,
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

                if (
                    role in {
                        "user",
                        "assistant",
                        "system",
                    }
                    and content
                ):
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

    # ---------------------------------------------------------
    # NORMAL THINKING
    # ---------------------------------------------------------

    def think(
        self,
        system_instruction: str,
        user_message: str,
        conversation: list[dict] | None = None,
    ) -> ProviderResult:

        if not self.client:
            raise RuntimeError(
                "Groq provider is not configured."
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
                "Groq returned an empty response."
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
            structured=False,
        )

    # ---------------------------------------------------------
    # STRUCTURED THINKING
    # ---------------------------------------------------------

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
                "Groq provider is not configured."
            )

        messages = self._build_messages(
            system_instruction,
            user_message,
            conversation,
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,

            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                },
            },

            max_completion_tokens=4096,

            # GPT-OSS is a reasoning model.
            # Hide reasoning tokens so the response channel
            # contains only the structured JSON requested above.
            reasoning_format="hidden",

            # Medium is the documented default for GPT-OSS,
            # but specifying it explicitly makes the provider
            # behavior deterministic.
            reasoning_effort="medium",
        )

        message = response.choices[0].message

        content = message.content

        if not content:
            raise RuntimeError(
                "Groq structured output returned empty content."
            )

        try:
            data = json.loads(
                content
            )

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Groq returned invalid JSON: {exc}"
            ) from exc

        if not isinstance(
            data,
            dict,
        ):
            raise RuntimeError(
                "Groq structured output must be a JSON object."
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

    # ---------------------------------------------------------
    # TOOL CALLING
    # ---------------------------------------------------------

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
                "Groq provider is not configured."
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
                reasoning_format="hidden",
            )

            message = response.choices[0].message

            tool_calls = (
                message.tool_calls
                or []
            )

            if tool_calls:

                messages.append(
                    {
                        "role": "assistant",
                        "content": (
                            message.content
                            or ""
                        ),
                        "tool_calls": [
                            {
                                "id": call.id,
                                "type": "function",
                                "function": {
                                    "name": (
                                        call.function.name
                                    ),
                                    "arguments": (
                                        call.function.arguments
                                    ),
                                },
                            }
                            for call in tool_calls
                        ],
                    }
                )

                for call in tool_calls:

                    try:
                        arguments = json.loads(
                            call.function.arguments
                            or "{}"
                        )

                    except json.JSONDecodeError as exc:
                        raise RuntimeError(
                            "Invalid tool arguments "
                            f"from Groq: {exc}"
                        ) from exc

                    try:
                        result = tool_executor(
                            call.function.name,
                            arguments,
                        )

                    except Exception as exc:
                        result = {
                            "success": False,
                            "error": str(exc),
                        }

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": json.dumps(
                                result,
                                default=str,
                            ),
                        }
                    )

                continue

            content = (
                message.content
                or ""
            )

            if not content:
                raise RuntimeError(
                    "Groq returned an empty final response."
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
                structured=False,
            )

        raise RuntimeError(
            "Groq reached the maximum of "
            f"{max_iterations} tool iterations."
        )


groq = GroqProvider()