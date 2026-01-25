"""Action provider configuration data structures."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ActionProviderConfig:
    """Configuration for the LLM action provider.

    Attributes:
        max_retries: Maximum number of retry attempts on parse failure.
        temperature: LLM sampling temperature.
        max_output_tokens: Maximum tokens in LLM response.
    """

    max_retries: int
    temperature: float
    max_output_tokens: int

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ValueError(
                f"max_retries cannot be negative: {self.max_retries}"
            )
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(
                f"temperature must be between 0.0 and 2.0: {self.temperature}"
            )
        if self.max_output_tokens <= 0:
            raise ValueError(
                f"max_output_tokens must be positive: {self.max_output_tokens}"
            )
