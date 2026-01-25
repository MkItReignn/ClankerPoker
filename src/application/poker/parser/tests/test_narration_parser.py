"""Tests for ThoughtProcessNarrationParser behavior and edge cases."""

import pytest

from src.application.poker.parser.narration_parser import (
    ThoughtProcessNarrationParser,
)
from src.application.protocols.response import ParseError
from src.domain.models.narration import Narration


@pytest.fixture
def parser():
    return ThoughtProcessNarrationParser()


class TestThoughtProcessExtraction:
    """Tests for extracting THOUGHT_PROCESS from response."""

    def test_extracts_thought_process(
        self, parser, full_thought_process_response
    ):
        result = parser.parse(full_thought_process_response)

        assert isinstance(result, Narration)
        assert "37 big blind stack" in result.thought_process
        assert "button" in result.thought_process
        assert "70-75%" in result.thought_process

    def test_returns_narration_object_type(
        self, parser, full_thought_process_response
    ):
        result = parser.parse(full_thought_process_response)

        assert isinstance(result, Narration)
        assert hasattr(result, "thought_process")

    def test_extracts_until_action(self, parser):
        response = """
THOUGHT_PROCESS:
This is my analysis of the hand.

ACTION: fold
"""
        result = parser.parse(response)

        assert isinstance(result, Narration)
        assert "ACTION" not in result.thought_process
        assert "fold" not in result.thought_process
        assert "analysis of the hand" in result.thought_process


class TestMissingField:
    """Tests for handling missing THOUGHT_PROCESS field."""

    def test_missing_thought_process_returns_error(self, parser):
        response = """
ACTION: fold
"""
        result = parser.parse(response)

        assert isinstance(result, ParseError)
        assert "THOUGHT_PROCESS" in result.message

    def test_empty_thought_process_returns_error(self, parser):
        response = """
THOUGHT_PROCESS:

ACTION: fold
"""
        result = parser.parse(response)

        assert isinstance(result, ParseError)
        assert "empty" in result.message.lower()

    def test_empty_with_only_whitespace_returns_error(self, parser):
        """THOUGHT_PROCESS with only spaces/tabs before ACTION returns error."""
        response = """
THOUGHT_PROCESS:

ACTION: fold
"""
        result = parser.parse(response)

        assert isinstance(result, ParseError)
        assert "empty" in result.message.lower()

    def test_empty_with_multiple_blank_lines_returns_error(self, parser):
        """THOUGHT_PROCESS with multiple blank lines before ACTION returns error."""
        response = """
THOUGHT_PROCESS:



ACTION: fold
"""
        result = parser.parse(response)

        assert isinstance(result, ParseError)
        assert "empty" in result.message.lower()

    def test_does_not_capture_action_line_as_content(self, parser):
        """Verify ACTION: line is never captured as thought process content."""
        response = """
THOUGHT_PROCESS:

ACTION: fold
"""
        result = parser.parse(response)

        # Should be an error, not a Narration with "ACTION: fold" as content
        assert isinstance(result, ParseError)
        if hasattr(result, "context") and result.context:
            # If there's context, it should not show ACTION as the captured content
            pass  # The error itself proves ACTION wasn't treated as content


class TestCaseInsensitivity:
    """Tests for case-insensitive field name parsing."""

    def test_lowercase_field_name(self, parser):
        response = """
thought_process:
This is my analysis.

ACTION: fold
"""
        result = parser.parse(response)

        assert isinstance(result, Narration)
        assert "analysis" in result.thought_process

    def test_mixed_case_field_name(self, parser):
        response = """
Thought_Process:
This is my analysis.

ACTION: fold
"""
        result = parser.parse(response)

        assert isinstance(result, Narration)
        assert "analysis" in result.thought_process


class TestWordLimitTrimming:
    """Tests for word limit enforcement and trimming."""

    def test_content_within_limit_passes(self, parser):
        short_content = (
            "This is a short thought process. It should pass without trimming."
        )
        response = f"""
THOUGHT_PROCESS:
{short_content}

ACTION: fold
"""
        result = parser.parse(response)

        assert isinstance(result, Narration)
        assert "short thought process" in result.thought_process

    def test_content_over_limit_gets_trimmed(self, parser):
        # Create content with multiple sentences, last one pushes over limit
        sentence1 = " ".join(["word"] * 200) + "."
        sentence2 = " ".join(["word"] * 200) + "."
        sentence3 = " ".join(["word"] * 250) + "."  # This should get trimmed
        over_limit_content = f"{sentence1} {sentence2} {sentence3}"

        response = f"""
THOUGHT_PROCESS:
{over_limit_content}

ACTION: fold
"""
        result = parser.parse(response)

        assert isinstance(result, Narration)
        # Should be trimmed to within 600 word limit
        word_count = len(result.thought_process.split())
        assert word_count <= 550

    def test_single_long_sentence_trimmed_to_empty_returns_error(self, parser):
        # A single sentence with 700+ words that exceeds limit
        # When trimmed, nothing remains
        single_long_sentence = " ".join(["word"] * 700)

        response = f"""
THOUGHT_PROCESS:
{single_long_sentence}

ACTION: fold
"""
        result = parser.parse(response)

        assert isinstance(result, ParseError)
        assert "trimmed to empty" in result.message.lower()


class TestWhitespaceCleanup:
    """Tests for whitespace normalization."""

    def test_multiple_spaces_collapsed(self, parser):
        response = """
THOUGHT_PROCESS:
Looking at    the board,    I see    opportunity.

ACTION: fold
"""
        result = parser.parse(response)

        assert isinstance(result, Narration)
        assert "Looking at the board" in result.thought_process
        assert "    " not in result.thought_process

    def test_preserves_paragraph_breaks(self, parser):
        response = """
THOUGHT_PROCESS:
First paragraph of analysis.

Second paragraph continues.

ACTION: fold
"""
        result = parser.parse(response)

        assert isinstance(result, Narration)
        # Content should be preserved (paragraph breaks may be normalized)
        assert "First paragraph" in result.thought_process
        assert "Second paragraph" in result.thought_process


class TestMinimalValidResponse:
    """Tests for responses without THOUGHT_PROCESS."""

    def test_action_only_response_returns_error(
        self, parser, minimal_response
    ):
        result = parser.parse(minimal_response)

        assert isinstance(result, ParseError)


class TestErrorContext:
    """Tests for error context information."""

    def test_missing_field_error_includes_snippet(self, parser):
        response = """
ACTION: fold
"""
        result = parser.parse(response)

        assert isinstance(result, ParseError)
        assert result.context is not None
        assert "response_snippet" in result.context

    def test_error_includes_truncated_snippet_for_long_response(self, parser):
        long_response = "ACTION: fold\n" + "x" * 300

        result = parser.parse(long_response)

        assert isinstance(result, ParseError)
        assert result.context is not None
        assert "response_snippet" in result.context
        assert len(result.context["response_snippet"]) <= 200
