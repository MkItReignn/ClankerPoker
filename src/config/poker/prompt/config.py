"""Poker prompt configuration data structures.

Contains the data classes for prompt components that can be composed together.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SystemPromptComponents:
    """System prompt components that can be composed together.

    Attributes:
        identity: Elite player identity, expertise, and mission.
        context_format_guide: Complete guide to reading structured context.
        history_notation: Action shorthand and position abbreviations.
        decision_framework: 9-category systematic decision framework.
        personality_section: Template for personality injection.
    """

    identity: str
    context_format_guide: str
    history_notation: str
    decision_framework: str
    personality_section: str

    def __post_init__(self) -> None:
        if not self.identity:
            raise ValueError("identity cannot be empty")
        if not self.context_format_guide:
            raise ValueError("context_format_guide cannot be empty")
        if not self.history_notation:
            raise ValueError("history_notation cannot be empty")
        if not self.decision_framework:
            raise ValueError("decision_framework cannot be empty")
        if not self.personality_section:
            raise ValueError("personality_section cannot be empty")


@dataclass(frozen=True, slots=True)
class UserPromptComponents:
    """User prompt components.

    Attributes:
        response_format: How to format the response (ACTION + REASONING).
        complete_example: Full example showing proper format and reasoning.
    """

    response_format: str
    complete_example: str

    def __post_init__(self) -> None:
        if not self.response_format:
            raise ValueError("response_format cannot be empty")
        if not self.complete_example:
            raise ValueError("complete_example cannot be empty")


@dataclass(frozen=True, slots=True)
class RetryPromptComponents:
    """Retry prompt components that can be composed together.

    Attributes:
        header: Retry header message.
        error_section: Template for error message.
        response_section: Template for previous response snippet.
        footer: Retry footer message with common errors and fixes.
    """

    header: str
    error_section: str
    response_section: str
    footer: str

    def __post_init__(self) -> None:
        if not self.header:
            raise ValueError("header cannot be empty")
        if not self.error_section:
            raise ValueError("error_section cannot be empty")
        if not self.response_section:
            raise ValueError("response_section cannot be empty")
        if not self.footer:
            raise ValueError("footer cannot be empty")


@dataclass(frozen=True, slots=True)
class PokerPromptConfig:
    """Poker prompt templates loaded from YAML.

    Contains structured, composable prompt components.

    Attributes:
        system_prompt: System prompt components.
        user_prompt: User prompt components.
        retry_prompt: Retry prompt components.
    """

    system_prompt: SystemPromptComponents
    user_prompt: UserPromptComponents
    retry_prompt: RetryPromptComponents
