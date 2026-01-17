"""Protocols for parsing LLM responses into actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

# Generic type variables
TAction = TypeVar("TAction")
TNarration = TypeVar("TNarration")
TAvailableActions = TypeVar("TAvailableActions", contravariant=True)


@dataclass(frozen=True, slots=True)
class ParseResult(Generic[TAction, TNarration]):
    """Result of parsing an LLM response.

    Either contains a successfully parsed action and optional narration,
    or an error message explaining why parsing failed.

    Attributes:
        action: The parsed action, or None if parsing failed.
        narration: Optional structured narration, or None.
        reasoning: Optional raw reasoning text from the LLM.
        error: Error message if parsing failed, or None.
    """

    action: TAction | None
    narration: TNarration | None = None
    reasoning: str | None = None
    error: str | None = None

    def __post_init__(self) -> None:
        if self.action is None and self.error is None:
            raise ValueError("ParseResult must have either action or error")
        if self.action is not None and self.error is not None:
            raise ValueError("ParseResult cannot have both action and error")

    @property
    def is_success(self) -> bool:
        """Whether parsing succeeded."""
        return self.action is not None

    @property
    def is_error(self) -> bool:
        """Whether parsing failed."""
        return self.error is not None

    @classmethod
    def success(
        cls,
        action: TAction,
        narration: TNarration | None = None,
        reasoning: str | None = None,
    ) -> ParseResult[TAction, TNarration]:
        """Create a successful parse result."""
        return cls(action=action, narration=narration, reasoning=reasoning)

    @classmethod
    def failure(cls, error: str) -> ParseResult[TAction, TNarration]:
        """Create a failed parse result."""
        return cls(action=None, error=error)


class ResponseParser(Protocol[TAction, TNarration, TAvailableActions]):
    """Protocol for parsing LLM responses into game actions.

    Responsible for extracting structured action and narration from
    raw LLM text output, validating against available actions.

    Type Parameters:
        TAction: The action type to parse into.
        TNarration: The narration type for structured output.
        TAvailableActions: The available actions type for validation.
    """

    def parse_response(
        self,
        response_text: str,
        available_actions: TAvailableActions,
    ) -> ParseResult[TAction, TNarration]:
        """Parse an LLM response into an action.

        Args:
            response_text: The raw text response from the LLM.
            available_actions: The set of legal actions for validation.

        Returns:
            ParseResult containing the action or an error message.
        """
        ...
