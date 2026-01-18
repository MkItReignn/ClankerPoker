"""Narration parsing strategy for poker responses."""

from __future__ import annotations

import re
from typing import ClassVar, Protocol

from src.application.protocols.response import ParseError, ParseErrorType
from src.domain.models.narration import Narration, NarrationText


class NarrationParser(Protocol):
    """Protocol for parsing structured narration from response text."""

    def parse(self, response_text: str) -> Narration | ParseError:
        """Parse structured narration from the response.

        Args:
            response_text: The full LLM response text.

        Returns:
            Narration if parsing succeeded, or ParseError if it failed.
        """
        ...


class StructuredNarrationParser:
    """Parses structured 9-field narration from poker responses.

    Extracts all 9 narration fields from the LLM response. Returns None if any
    field is missing or empty, allowing backward compatibility with responses
    that only contain ACTION + REASONING.
    """

    # Word count limits for narration fields (with 20% tolerance)
    # Source: src/domain/models/narration.py lines 71-136
    NARRATION_WORD_LIMITS: ClassVar[dict[str, int]] = {
        "game_stage_assessment": 96,  # 80 + 20%
        "positional_context": 72,  # 60 + 20%
        "range_analysis": 120,  # 100 + 20%
        "equity_assessment": 96,  # 80 + 20%
        "opponent_modeling": 84,  # 70 + 20%
        "bet_sizing_rationale": 72,  # 60 + 20%
        "multi_street_plan": 96,  # 80 + 20%
        "meta_considerations": 84,  # 70 + 20%
        "final_decision": 60,  # 50 + 20%
    }

    # Patterns for narration fields
    NARRATION_FIELD_PATTERNS: ClassVar[dict[str, re.Pattern[str]]] = {
        "game_stage_assessment": re.compile(
            r"GAME_STAGE_ASSESSMENT:\s*(.+?)(?=\n\s*(?:POSITIONAL_CONTEXT|ACTION|$))",
            re.IGNORECASE | re.DOTALL,
        ),
        "positional_context": re.compile(
            r"POSITIONAL_CONTEXT:\s*(.+?)(?=\n\s*(?:RANGE_ANALYSIS|ACTION|$))",
            re.IGNORECASE | re.DOTALL,
        ),
        "range_analysis": re.compile(
            r"RANGE_ANALYSIS:\s*(.+?)(?=\n\s*(?:EQUITY_ASSESSMENT|ACTION|$))",
            re.IGNORECASE | re.DOTALL,
        ),
        "equity_assessment": re.compile(
            r"EQUITY_ASSESSMENT:\s*(.+?)(?=\n\s*(?:OPPONENT_MODELING|ACTION|$))",
            re.IGNORECASE | re.DOTALL,
        ),
        "opponent_modeling": re.compile(
            r"OPPONENT_MODELING:\s*(.+?)(?=\n\s*(?:BET_SIZING_RATIONALE|ACTION|$))",
            re.IGNORECASE | re.DOTALL,
        ),
        "bet_sizing_rationale": re.compile(
            r"BET_SIZING_RATIONALE:\s*(.+?)(?=\n\s*(?:MULTI_STREET_PLAN|ACTION|$))",
            re.IGNORECASE | re.DOTALL,
        ),
        "multi_street_plan": re.compile(
            r"MULTI_STREET_PLAN:\s*(.+?)(?=\n\s*(?:META_CONSIDERATIONS|ACTION|$))",
            re.IGNORECASE | re.DOTALL,
        ),
        "meta_considerations": re.compile(
            r"META_CONSIDERATIONS:\s*(.+?)(?=\n\s*(?:FINAL_DECISION|ACTION|$))",
            re.IGNORECASE | re.DOTALL,
        ),
        "final_decision": re.compile(
            r"FINAL_DECISION:\s*(.+?)(?=\n\s*(?:ACTION|REASONING|$))", re.IGNORECASE | re.DOTALL
        ),
    }

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
        # Check if already within limit
        word_count = len(text.split())
        if word_count <= max_words:
            return text

        # Split into sentences (handle ., !, ?)
        # Use regex to split on sentence boundaries while preserving the delimiter
        sentences = re.split(r"(?<=[.!?])\s+", text)

        # Remove empty sentences
        sentences = [s for s in sentences if s.strip()]

        if not sentences:
            return ""

        # Remove sentences from the end until within limit
        while sentences:
            current_text = " ".join(sentences)
            word_count = len(current_text.split())

            if word_count <= max_words:
                return current_text

            # Remove last sentence
            sentences.pop()

        # All sentences removed
        return ""

    def parse(self, response_text: str) -> Narration | ParseError:
        """Parse structured narration from the response.

        Extracts all 9 narration fields from the LLM response. Returns error if any
        field is missing or empty.

        Args:
            response_text: The full LLM response text.

        Returns:
            Narration if parsing succeeded, or ParseError if it failed.
        """
        # Extract all fields
        fields: dict[str, str] = {}

        for field_name, pattern in self.NARRATION_FIELD_PATTERNS.items():
            match = pattern.search(response_text)
            if not match:
                # Field not found
                return ParseError.create(
                    ParseErrorType.INVALID_FORMAT,
                    f"Narration field '{field_name}' not found in response",
                    context={
                        "missing_field": field_name,
                        "response_snippet": (
                            response_text[:200] if len(response_text) > 200 else response_text
                        ),
                    },
                )

            # Extract and clean the content
            content = match.group(1).strip()

            # Check for empty content (whitespace only)
            if not content:
                return ParseError.create(
                    ParseErrorType.INVALID_FORMAT,
                    f"Narration field '{field_name}' is empty",
                    context={
                        "empty_field": field_name,
                        "response_snippet": (
                            response_text[:200] if len(response_text) > 200 else response_text
                        ),
                    },
                )

            # Clean up extra whitespace while preserving paragraph breaks
            # Replace multiple spaces with single space
            content = re.sub(r" +", " ", content)
            # Replace 3+ newlines with just 2 (preserve paragraph breaks)
            content = re.sub(r"\n{3,}", "\n\n", content)

            # Validate and trim word count (with 20% tolerance)
            max_words = self.NARRATION_WORD_LIMITS[field_name]
            content = self._trim_to_word_limit(content, max_words)

            # After trimming, check if content is empty
            if not content:
                return ParseError.create(
                    ParseErrorType.INVALID_FORMAT,
                    f"Narration field '{field_name}' exceeded word limit and was trimmed to empty",
                    context={
                        "field_name": field_name,
                        "max_words": max_words,
                        "response_snippet": (
                            response_text[:200] if len(response_text) > 200 else response_text
                        ),
                    },
                )

            fields[field_name] = content

        # All fields present and non-empty - construct Narration
        try:
            return Narration(
                game_stage_assessment=NarrationText(fields["game_stage_assessment"]),
                positional_context=NarrationText(fields["positional_context"]),
                range_analysis=NarrationText(fields["range_analysis"]),
                equity_assessment=NarrationText(fields["equity_assessment"]),
                opponent_modeling=NarrationText(fields["opponent_modeling"]),
                bet_sizing_rationale=NarrationText(fields["bet_sizing_rationale"]),
                multi_street_plan=NarrationText(fields["multi_street_plan"]),
                meta_considerations=NarrationText(fields["meta_considerations"]),
                final_decision=NarrationText(fields["final_decision"]),
            )
        except (ValueError, KeyError) as e:
            # Narration validation failed (empty fields, etc.)
            return ParseError.create(
                ParseErrorType.INVALID_FORMAT,
                f"Failed to create Narration object: {e}",
                context={
                    "exception": str(e),
                    "response_snippet": (
                        response_text[:200] if len(response_text) > 200 else response_text
                    ),
                },
            )
