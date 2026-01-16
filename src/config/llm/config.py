"""LLM client configuration data structures."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OpenRouterConfig:
    """Configuration for OpenRouter HTTP client.

    Attributes:
        api_key: OpenRouter API key (required).
        base_url: Base URL for the OpenRouter API. Defaults to official endpoint.
        timeout: Request timeout in seconds. Defaults to 60.0.
    """

    api_key: str
    base_url: str = "https://openrouter.ai/api/v1"
    timeout: float = 60.0

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if not self.api_key:
            raise ValueError("api_key cannot be empty")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
