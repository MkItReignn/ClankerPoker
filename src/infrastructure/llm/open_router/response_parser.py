from __future__ import annotations

from src.application.protocols.llm import LlmApiError, LlmRequest, LlmResponse
from src.infrastructure.llm.open_router.model_mapper import OpenRouterModelMapper
from src.infrastructure.llm.open_router.response import (
    OpenRouterApiResponse, OpenRouterResponseChoice, OpenRouterResponseMessage,
    OpenRouterResponseUsage)


class OpenRouterResponseParser:
    @staticmethod
    def parse(data: dict[str, object]) -> OpenRouterApiResponse:
        choices_raw = data.get("choices", [])
        if not isinstance(choices_raw, list) or not choices_raw:
            raise LlmApiError("No choices in response")

        choices: list[OpenRouterResponseChoice] = []
        for idx, choice_raw in enumerate(choices_raw):
            if not isinstance(choice_raw, dict):
                raise LlmApiError(f"Invalid choice format at index {idx}")

            message_raw = choice_raw.get("message", {})
            if not isinstance(message_raw, dict):
                raise LlmApiError(f"Invalid message format in choice {idx}")

            message = OpenRouterResponseMessage(
                role=str(message_raw.get("role", "")),
                content=str(message_raw.get("content", "")),
            )

            index_raw = choice_raw.get("index", idx)
            index = int(index_raw) if isinstance(index_raw, int | str) else idx

            choice = OpenRouterResponseChoice(
                index=index,
                message=message,
                finish_reason=str(choice_raw.get("finish_reason", "unknown")),
            )
            choices.append(choice)

        usage: OpenRouterResponseUsage | None = None
        usage_raw = data.get("usage")
        if usage_raw is not None and isinstance(usage_raw, dict):
            prompt_tokens_raw = usage_raw.get("prompt_tokens", 0)
            prompt_tokens = (
                int(prompt_tokens_raw) if isinstance(prompt_tokens_raw, int | str) else 0
            )

            completion_tokens_raw = usage_raw.get("completion_tokens", 0)
            completion_tokens = (
                int(completion_tokens_raw) if isinstance(completion_tokens_raw, int | str) else 0
            )

            total_tokens_raw = usage_raw.get("total_tokens")
            total_tokens = (
                int(total_tokens_raw)
                if total_tokens_raw is not None and isinstance(total_tokens_raw, int | str)
                else None
            )

            usage = OpenRouterResponseUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            )

        created_raw = data.get("created", 0)
        created = int(created_raw) if isinstance(created_raw, int | str) else 0

        return OpenRouterApiResponse(
            id=str(data.get("id", "")),
            choices=choices,
            created=created,
            model=str(data.get("model", "")),
            object=str(data.get("object", "chat.completion")),
            usage=usage,
            raw_data=data,
        )

    @staticmethod
    def to_llm_response(api_response: OpenRouterApiResponse, request: LlmRequest) -> LlmResponse:
        if not api_response.choices:
            raise LlmApiError("No choices in response")

        first_choice = api_response.choices[0]
        content = first_choice.message.content
        finish_reason = first_choice.finish_reason

        prompt_tokens = api_response.usage.prompt_tokens if api_response.usage else 0
        completion_tokens = api_response.usage.completion_tokens if api_response.usage else 0
        model_id = OpenRouterModelMapper.from_openrouter_model(api_response.model)


        return LlmResponse(
            content=content,
            model_id=model_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            finish_reason=finish_reason,
            raw_response=api_response.raw_data,
        )
