"""Protocols for parsing LLM responses into actions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, Protocol, TypeVar

# Generic type variables
TAction = TypeVar("TAction")
TNarration = TypeVar("TNarration")
TAvailableActions = TypeVar("TAvailableActions", contravariant=True)


class ParseErrorType(str, Enum):
    """Base error types for parsing failures.

    Games can extend this or use their own error types.
    String enum allows easy serialization and extensibility.
    """

    NO_ACTION_FOUND = "NO_ACTION_FOUND"
    INVALID_ACTION_TYPE = "INVALID_ACTION_TYPE"
    AMOUNT_OUT_OF_RANGE = "AMOUNT_OUT_OF_RANGE"
    AMOUNT_BELOW_MIN = "AMOUNT_BELOW_MIN"
    AMOUNT_ABOVE_MAX = "AMOUNT_ABOVE_MAX"
    ACTION_NOT_AVAILABLE = "ACTION_NOT_AVAILABLE"
    INVALID_FORMAT = "INVALID_FORMAT"
    EMPTY_RESPONSE = "EMPTY_RESPONSE"


@dataclass(frozen=True, slots=True)
class ParseError:
    """Structured error information for parsing failures.

    Contains error type, message, and optional context for better diagnostics.
    """

    message: str
    error_type: str  # Use ParseErrorType enum values, or game-specific strings
    context: dict[str, Any] | None = (
        None  # Additional context (response snippet, available actions, etc.)
    )

    @classmethod
    def create(
        cls,
        error_type: ParseErrorType | str,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> ParseError:
        """Factory method for creating ParseError."""
        error_type_str = error_type.value if isinstance(error_type, Enum) else error_type
        return cls(message=message, error_type=error_type_str, context=context)


@dataclass(frozen=True, slots=True)
class ParseSuccess(Generic[TAction, TNarration]):
    """Successful parse result.

    Action parsing succeeded, so the game can progress.
    Narration may have failed - caller should handle with logging.

    Attributes:
        action: The successfully parsed action (guaranteed valid).
        narration: Parsed narration or ParseError if narration parsing failed.
    """

    action: TAction
    narration: TNarration | ParseError


@dataclass(frozen=True, slots=True)
class ParseFailure:
    """Failed parse result.

    Action parsing failed, so the game cannot progress.
    Caller should retry or fail the request.

    Attributes:
        error: Structured error information explaining the failure.
    """

    error: ParseError


# Type alias for parse results: discriminated union
# Use isinstance() to discriminate between success and failure
type ParseResult[TAction, TNarration] = ParseSuccess[TAction, TNarration] | ParseFailure


@dataclass(frozen=True, slots=True)
class ActionResponse(Generic[TAction, TNarration]):
    """Response from an action provider - contains chosen action and optional narration."""

    action: TAction
    narration: TNarration | None = None


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
            ParseSuccess if action parsing succeeded (narration/reasoning may have failed).
            ParseFailure if action parsing failed (game cannot progress).
        """
        ...
