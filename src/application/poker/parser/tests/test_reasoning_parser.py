"""Tests for RegexReasoningParser behavior and edge cases."""

import pytest

from src.application.poker.parser.reasoning_parser import RegexReasoningParser
from src.application.protocols.response import ParseError, ParseErrorType


@pytest.fixture
def parser():
    return RegexReasoningParser()


class TestReasoningExtraction:
    """Tests for extracting reasoning from response."""

    def test_extracts_simple_reasoning(self, parser):
        response = """
ACTION: fold

REASONING:
Hand is too weak to continue.
"""
        result = parser.parse(response)

        assert isinstance(result, str)
        assert "too weak" in result

    def test_extracts_multiline_reasoning(self, parser):
        response = """
ACTION: raise 300

REASONING:
Value raise with position advantage.
Opponent is likely to call with weaker hands.
Building the pot for future streets.
"""
        result = parser.parse(response)

        assert isinstance(result, str)
        assert "Value raise" in result
        assert "future streets" in result

    def test_extracts_reasoning_from_full_response(self, parser, full_narration_response):
        result = parser.parse(full_narration_response)

        assert isinstance(result, str)
        assert "Value raise" in result


class TestCaseInsensitivity:
    """Tests for case-insensitive reasoning label."""

    def test_uppercase_reasoning(self, parser):
        response = "REASONING: Hand is weak."
        result = parser.parse(response)
        assert isinstance(result, str)

    def test_lowercase_reasoning(self, parser):
        response = "reasoning: Hand is weak."
        result = parser.parse(response)
        assert isinstance(result, str)

    def test_mixed_case_reasoning(self, parser):
        response = "Reasoning: Hand is weak."
        result = parser.parse(response)
        assert isinstance(result, str)


class TestMissingReasoning:
    """Tests for handling missing reasoning."""

    def test_no_reasoning_returns_error(self, parser):
        response = """
ACTION: fold
"""
        result = parser.parse(response)

        assert isinstance(result, ParseError)
        assert result.error_type == ParseErrorType.INVALID_FORMAT.value
        assert "REASONING" in result.message

    def test_empty_response_returns_error(self, parser):
        response = ""
        result = parser.parse(response)

        assert isinstance(result, ParseError)

    def test_malformed_reasoning_returns_error(self, parser):
        response = "REASONING Hand is weak"  # Missing colon
        result = parser.parse(response)

        assert isinstance(result, ParseError)


class TestWhitespaceHandling:
    """Tests for whitespace handling in reasoning."""

    def test_trims_leading_whitespace(self, parser):
        response = "REASONING:    Hand is weak."
        result = parser.parse(response)

        assert isinstance(result, str)
        assert result.startswith("Hand")

    def test_trims_trailing_whitespace(self, parser):
        response = "REASONING: Hand is weak.   "
        result = parser.parse(response)

        assert isinstance(result, str)
        assert result.endswith("weak.")

    def test_reasoning_before_double_newline(self, parser):
        response = """
REASONING:
First part of reasoning.

Some other section follows.
"""
        result = parser.parse(response)

        assert isinstance(result, str)
        assert "First part" in result
        assert "Some other" not in result


class TestReasoningPosition:
    """Tests for reasoning at different positions in response."""

    def test_reasoning_at_start(self, parser):
        response = "REASONING: Opening reasoning."
        result = parser.parse(response)
        assert isinstance(result, str)
        assert result == "Opening reasoning."

    def test_reasoning_after_action(self, parser):
        response = """
ACTION: fold

REASONING: After action.
"""
        result = parser.parse(response)
        assert isinstance(result, str)
        assert "After action" in result

    def test_reasoning_in_middle_of_text(self, parser):
        response = """
Some preamble text here.

REASONING: The actual reasoning.

Some postamble text.
"""
        result = parser.parse(response)
        assert isinstance(result, str)
        assert "actual reasoning" in result


class TestErrorContext:
    """Tests for error context information."""

    def test_error_includes_response_snippet(self, parser):
        long_response = "x" * 300

        result = parser.parse(long_response)

        assert isinstance(result, ParseError)
        assert result.context is not None
        assert "response_snippet" in result.context
        assert len(result.context["response_snippet"]) <= 200

    def test_short_response_included_fully(self, parser):
        short_response = "No reasoning here"

        result = parser.parse(short_response)

        assert isinstance(result, ParseError)
        assert result.context is not None
        assert result.context["response_snippet"] == short_response
