from __future__ import annotations

from dataclasses import dataclass, field


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
    raw_data: dict[str, object] = field(default_factory=dict)
