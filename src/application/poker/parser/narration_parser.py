"""Narration parsing strategy for poker responses."""

import re
from typing import ClassVar, Protocol

from src.application.protocols.response import ParseError, ParseErrorType
from src.domain.models.narration import Narration, NarrationText


class NarrationParser(Protocol):
    """Protocol for parsing narration from response text."""

    def parse(self, response_text: str) -> Narration | ParseError:
        """Parse narration from the response.

        Args:
            response_text: The full LLM response text.

        Returns:
            Narration if parsing succeeded, or ParseError if it failed.
        """
        ...


class ThoughtProcessNarrationParser:
    """Parses stream-of-consciousness THOUGHT_PROCESS from poker responses.

    Extracts the single thought_process field from the LLM response.
    Returns ParseError if the field is missing or empty.
    """

    # Word count limit for thought_process (500 target + 10% tolerance = 550)
    MAX_WORDS: ClassVar[int] = 550

    # Pattern to extract THOUGHT_PROCESS content
    # - [ \t]* matches only horizontal whitespace after colon (not newlines)
    # - \n? optionally matches a single newline
    # - (.*?) captures content (can be empty)
    # - (?=\n[ \t]*ACTION:|\Z) stops at newline before ACTION: or end of string
    THOUGHT_PROCESS_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"THOUGHT_PROCESS:[ \t]*\n?(.*?)(?=\n[ \t]*ACTION:|\Z)",
        re.IGNORECASE | re.DOTALL,
    )

    def _trim_to_word_limit(self, text: str, max_words: int) -> str:
        """Trim text to word limit by removing sentences from the end.

        If text exceeds max_words, removes the last sentence and rechecks.
        Repeats until text is within limit or empty.

        Args:
            text: The text to trim.
            max_words: Maximum number of words allowed.

        Returns:
            Trimmed text within word limit, or empty string if all sentences removed.
        """
        word_count = len(text.split())
        if word_count <= max_words:
            return text

        sentences = re.split(r"(?<=[.!?])\s+", text)
        sentences = [s for s in sentences if s.strip()]

        if not sentences:
            return ""

        while sentences:
            current_text = " ".join(sentences)
            word_count = len(current_text.split())

            if word_count <= max_words:
                return current_text

            sentences.pop()

        return ""

    def parse(self, response_text: str) -> Narration | ParseError:
        """Parse THOUGHT_PROCESS narration from the response.

        Args:
            response_text: The full LLM response text.

        Returns:
            Narration if parsing succeeded, or ParseError if it failed.
        """
        match = self.THOUGHT_PROCESS_PATTERN.search(response_text)

        if not match:
            return ParseError.create(
                ParseErrorType.INVALID_FORMAT,
                "THOUGHT_PROCESS field not found in response",
                context={
                    "response_snippet": (
                        response_text[:200]
                        if len(response_text) > 200
                        else response_text
                    ),
                },
            )

        content = match.group(1).strip()

        if not content:
            return ParseError.create(
                ParseErrorType.INVALID_FORMAT,
                "THOUGHT_PROCESS field is empty",
                context={
                    "response_snippet": (
                        response_text[:200]
                        if len(response_text) > 200
                        else response_text
                    ),
                },
            )

        # Clean up whitespace while preserving paragraph breaks
        content = re.sub(r" +", " ", content)
        content = re.sub(r"\n{3,}", "\n\n", content)

        # Trim to word limit if needed
        content = self._trim_to_word_limit(content, self.MAX_WORDS)

        if not content:
            return ParseError.create(
                ParseErrorType.INVALID_FORMAT,
                "THOUGHT_PROCESS exceeded word limit and was trimmed to empty",
                context={"max_words": self.MAX_WORDS},
            )

        try:
            return Narration(thought_process=NarrationText(content))
        except ValueError as e:
            return ParseError.create(
                ParseErrorType.INVALID_FORMAT,
                f"Failed to create Narration object: {e}",
                context={"exception": str(e)},
            )
