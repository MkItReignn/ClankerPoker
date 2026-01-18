"""Reasoning parsing strategy for poker responses."""

from __future__ import annotations

import re
from typing import Protocol

from src.application.protocols.response import ParseError, ParseErrorType


class ReasoningParser(Protocol):
    """Protocol for parsing reasoning from response text."""

    def parse(self, response_text: str) -> str | ParseError:
        """Parse reasoning from the response.

        Args:
            response_text: The full LLM response text.

        Returns:
            Reasoning string if parsing succeeded, or ParseError if it failed.
        """
        ...


class RegexReasoningParser:
    """Regex-based reasoning parser for poker responses.

    Extracts REASONING: <text> pattern from LLM responses.
    """

    # Pattern to extract reasoning
    REASONING_PATTERN = re.compile(
        r"REASONING:\s*(.+?)(?=\n\n|\Z)",
        re.IGNORECASE | re.DOTALL,
    )

    def parse(self, response_text: str) -> str | ParseError:
        match = self.REASONING_PATTERN.search(response_text)
        if match:
            return match.group(1).strip()

        return ParseError.create(
            ParseErrorType.INVALID_FORMAT,
            "Could not find valid REASONING in response. " "Expected format: REASONING: <text>",
            context={
                "response_snippet": (
                    response_text[:200] if len(response_text) > 200 else response_text
                ),
            },
        )
