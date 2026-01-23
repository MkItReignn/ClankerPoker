"""Protocols for LLM client communication."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Self

from src.domain.models.llm_model import LlmModel


@dataclass(frozen=True, slots=True)
class LlmRequest:
    """Request to send to an LLM.

    Attributes:
        system_prompt: The system prompt setting context and behavior.
        user_prompt: The user prompt containing the actual request.
        model_id: The model identifier to use.
        max_tokens: Maximum tokens in the response.
        temperature: Sampling temperature (0.0-2.0). Controls randomness in output:
            - 0.0: Most deterministic, always selects the most likely token.
            - 0.0-0.7: Low temperature, focused and consistent responses.
            - 0.7-1.0: Medium temperature, balanced creativity and consistency.
            - 1.0-2.0: High temperature, more creative and varied responses.
            Lower values produce more predictable outputs; higher values increase diversity.
    """

    system_prompt: str
    user_prompt: str
    model_id: LlmModel
    max_tokens: int = 2048
    temperature: float = 0.7

    def __post_init__(self) -> None:
        if not self.system_prompt:
            raise ValueError("system_prompt cannot be empty")
        if not self.user_prompt:
            raise ValueError("user_prompt cannot be empty")
        if self.max_tokens <= 0:
            raise ValueError(f"max_tokens must be positive: {self.max_tokens}")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(f"temperature must be between 0.0 and 2.0: {self.temperature}")


@dataclass(frozen=True, slots=True)
class LlmResponse:
    """Response from an LLM.

    Attributes:
        content: The text content of the response.
        model_id: The model that generated this response.
        prompt_tokens: Number of tokens in the prompt.
        completion_tokens: Number of tokens in the completion.
        finish_reason: Why the response ended (stop, length, etc.).
        raw_response: Optional raw response data for debugging.
    """

    content: str
    model_id: LlmModel
    prompt_tokens: int
    completion_tokens: int
    finish_reason: str
    raw_response: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.prompt_tokens < 0:
            raise ValueError(f"prompt_tokens cannot be negative: {self.prompt_tokens}")
        if self.completion_tokens < 0:
            raise ValueError(f"completion_tokens cannot be negative: {self.completion_tokens}")

    @property
    def total_tokens(self) -> int:
        """Total tokens used (prompt + completion)."""
        return self.prompt_tokens + self.completion_tokens


class LlmClient(Protocol):
    """Protocol for LLM API clients.

    This is a simple protocol for sending requests to LLMs and receiving responses.
    Implementations handle the actual API communication.
    """

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None: ...

    async def complete(self, request: LlmRequest) -> LlmResponse:
        """Send a request to the LLM and get a response.

        Args:
            request: The request containing prompts and configuration.

        Returns:
            The LLM's response.

        Raises:
            LlmError: If the API call fails.
        """
        ...


class LlmError(Exception):
    """Base exception for LLM-related errors."""

    pass


class LlmApiError(LlmError):
    """Error from the LLM API (rate limit, invalid request, etc.)."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class LlmTimeoutError(LlmError):
    """Timeout waiting for LLM response."""

    pass
