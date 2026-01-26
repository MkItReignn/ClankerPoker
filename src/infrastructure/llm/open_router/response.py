from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class FinishReason(StrEnum):
    """Normalized finish reasons from OpenRouter API.

    OpenRouter normalizes each model's finish_reason to one of these values.
    The original provider-specific reason is available in native_finish_reason.

    See: https://openrouter.ai/docs/api/reference/overview
    """

    STOP = "stop"
    LENGTH = "length"
    TOOL_CALLS = "tool_calls"
    CONTENT_FILTER = "content_filter"
    ERROR = "error"
    UNKNOWN = "unknown"

    @property
    def description(self) -> str:
        descriptions = {
            FinishReason.STOP: "Model completed response naturally or hit a stop sequence",
            FinishReason.LENGTH: "Response truncated due to max_tokens limit",
            FinishReason.TOOL_CALLS: "Model invoked a tool/function",
            FinishReason.CONTENT_FILTER: "Output blocked by content policy",
            FinishReason.ERROR: "Error occurred during generation",
            FinishReason.UNKNOWN: "Fallback for unrecognized values",
        }
        return descriptions[self]


@dataclass(frozen=True, slots=True)
class OpenRouterResponseMessage:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class OpenRouterResponseChoice:
    index: int
    message: OpenRouterResponseMessage
    finish_reason: str


@dataclass(frozen=True, slots=True)
class OpenRouterResponseUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class OpenRouterApiResponse:
    id: str
    choices: list[OpenRouterResponseChoice]
    created: int
    model: str
    object: str = "chat.completion"
    usage: OpenRouterResponseUsage | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)
