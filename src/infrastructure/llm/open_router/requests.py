from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ContentType(StrEnum):
    JSON = "application/json"


class MessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ResponseFormatType(StrEnum):
    JSON_OBJECT = "json_object"
    TEXT = "text"


@dataclass(frozen=True, slots=True)
class OpenRouterRequestHeaders:
    api_key: str
    content_type: ContentType = ContentType.JSON

    def to_dict(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": self.content_type.value,
        }


@dataclass(frozen=True, slots=True)
class ResponseFormat:
    response_type: ResponseFormatType = ResponseFormatType.TEXT

    def to_dict(self) -> dict[str, str]:
        return {"type": self.response_type.value}


@dataclass(frozen=True, slots=True)
class OpenRouterRequestMessage:
    role: MessageRole
    content: str

    def to_dict(self) -> dict[str, str]:
        return {
            "role": self.role.value,
            "content": self.content,
        }


@dataclass(frozen=True, slots=True)
class OpenRouterApiRequest:
    model: str
    messages: list[OpenRouterRequestMessage]
    max_tokens: int
    temperature: float
    response_format: ResponseFormat | None = None
    top_p: float | None = None
    top_k: int | None = None
    stop: list[str] | None = None
    stream: bool = False

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "model": self.model,
            "messages": [msg.to_dict() for msg in self.messages],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        if self.response_format is not None:
            payload["response_format"] = self.response_format.to_dict()

        if self.top_p is not None:
            payload["top_p"] = self.top_p

        if self.top_k is not None:
            payload["top_k"] = self.top_k

        if self.stop is not None:
            payload["stop"] = self.stop

        if self.stream:
            payload["stream"] = self.stream

        return payload
