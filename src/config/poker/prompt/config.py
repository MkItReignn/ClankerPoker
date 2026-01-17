"""Poker prompt configuration data structures.

Contains the data classes for prompt components that can be composed together.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SystemPromptComponents:
    """System prompt components that can be composed together.

    Attributes:
        base: Base system prompt with player identity and goals.
        personality_section: Template for personality injection.
        history_format_guide: Guide for reading hand history format.
    """

    base: str
    personality_section: str
    history_format_guide: str

    def __post_init__(self) -> None:
        if not self.base:
            raise ValueError("base cannot be empty")
        if not self.personality_section:
            raise ValueError("personality_section cannot be empty")
        if not self.history_format_guide:
            raise ValueError("history_format_guide cannot be empty")


@dataclass(frozen=True, slots=True)
class UserPromptComponents:
    """User prompt components.

    Attributes:
        action_format_instructions: Instructions for action response format.
    """

    action_format_instructions: str

    def __post_init__(self) -> None:
        if not self.action_format_instructions:
            raise ValueError("action_format_instructions cannot be empty")


@dataclass(frozen=True, slots=True)
class RetryPromptComponents:
    """Retry prompt components that can be composed together.

    Attributes:
        header: Retry header message.
        error_section: Template for error message.
        response_section: Template for previous response snippet.
        footer: Retry footer message.
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
