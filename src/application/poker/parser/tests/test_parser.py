"""Tests for PokerResponseParser composition and behavior."""

import pytest

from src.application.poker.parser.action_parser import PokerActionParser
from src.application.poker.parser.narration_parser import (
    ThoughtProcessNarrationParser,
)
from src.application.poker.parser.parser import PokerResponseParser
from src.application.protocols.response import (
    ParseError,
    ParseErrorType,
    ParseFailure,
    ParseSuccess,
)
from src.domain.models.actions import ActionType
from src.domain.models.available_action import (
    AvailableCallAction,
    AvailableCheckAction,
    AvailableFoldAction,
)
from src.domain.models.chips import ChipAmount
from src.domain.models.narration import Narration


@pytest.fixture
def parser():
    return PokerResponseParser()


class TestParseResponseSuccess:
    """Tests for successful response parsing."""

    def test_parses_full_response_with_narration(
        self, parser, preflop_actions
    ):
        response = """
THOUGHT_PROCESS:
I'm on the button with Ace-King suited and I've just flopped top pair
with the best possible kicker on a very dry board. This is an excellent
spot. The player in early position opened and continuation bet - their
range is likely polarized between strong King hands for value or missed
high cards like Ace-Queen or Ace-Jack. Against this range, I'm ahead
most of the time. Raising to 300 makes sense here.

ACTION: raise 300
"""
        result = parser.parse_response(response, preflop_actions)

        assert isinstance(result, ParseSuccess)
        assert result.action.action_type == ActionType.RAISE
        assert result.action.amount.value == 300
        assert isinstance(result.narration, Narration)
        assert "button" in result.narration.thought_process.lower()

    def test_parses_minimal_response(self, parser, preflop_actions):
        response = """
THOUGHT_PROCESS:
Hand is too weak to continue here. Need to fold.

ACTION: fold
"""
        result = parser.parse_response(response, preflop_actions)

        assert isinstance(result, ParseSuccess)
        assert result.action.action_type == ActionType.FOLD
        assert isinstance(result.narration, Narration)
        assert "weak" in result.narration.thought_process.lower()


class TestActionOnly:
    """Tests for responses with action but no thought process."""

    def test_action_only_still_works(self, parser, preflop_actions):
        response = "ACTION: fold"
        result = parser.parse_response(response, preflop_actions)

        assert isinstance(result, ParseSuccess)
        assert result.action.action_type == ActionType.FOLD
        assert isinstance(result.narration, ParseError)


class TestNarrationOptional:
    """Tests demonstrating narration is optional for success."""

    def test_missing_thought_process_still_succeeds(
        self, parser, preflop_actions
    ):
        response = """
ACTION: raise 300
"""
        result = parser.parse_response(response, preflop_actions)

        assert isinstance(result, ParseSuccess)
        assert isinstance(result.narration, ParseError)

    def test_empty_thought_process_still_succeeds(
        self, parser, preflop_actions
    ):
        response = """
THOUGHT_PROCESS:

ACTION: fold
"""
        result = parser.parse_response(response, preflop_actions)

        assert isinstance(result, ParseSuccess)
        assert isinstance(result.narration, ParseError)


class TestActionParseFailure:
    """Tests for handling action parse failures."""

    def test_no_action_returns_failure(self, parser, preflop_actions):
        response = "I think I should fold here but I'm not sure."
        result = parser.parse_response(response, preflop_actions)

        assert isinstance(result, ParseFailure)
        assert result.error.error_type == ParseErrorType.NO_ACTION_FOUND.value

    def test_invalid_action_returns_failure(self, parser, preflop_actions):
        response = "ACTION: bluff 1000"
        result = parser.parse_response(response, preflop_actions)

        assert isinstance(result, ParseFailure)

    def test_unavailable_action_returns_failure(self, parser, preflop_actions):
        response = "ACTION: check"  # Check not available preflop facing bet
        result = parser.parse_response(response, preflop_actions)

        assert isinstance(result, ParseFailure)
        assert (
            result.error.error_type
            == ParseErrorType.ACTION_NOT_AVAILABLE.value
        )


class TestFallbackAction:
    """Tests for get_fallback_action behavior."""

    def test_prefers_check_over_call(self, parser):
        actions = [
            AvailableFoldAction(),
            AvailableCheckAction(),
            AvailableCallAction(call_amount=ChipAmount(100)),
        ]
        fallback = parser.get_fallback_action(actions)

        assert fallback is not None
        assert fallback.action_type == ActionType.CHECK

    def test_prefers_call_over_fold(self, parser):
        actions = [
            AvailableFoldAction(),
            AvailableCallAction(call_amount=ChipAmount(100)),
        ]
        fallback = parser.get_fallback_action(actions)

        assert fallback is not None
        assert fallback.action_type == ActionType.CALL

    def test_falls_back_to_fold_when_no_check_or_call(self, parser):
        actions = [AvailableFoldAction()]
        fallback = parser.get_fallback_action(actions)

        assert fallback is not None
        assert fallback.action_type == ActionType.FOLD

    def test_returns_none_for_empty_actions(self, parser):
        fallback = parser.get_fallback_action([])
        assert fallback is None


class TestDependencyInjection:
    """Tests for custom parser injection."""

    def test_accepts_custom_action_parser(self, preflop_actions):
        custom_parser = PokerActionParser()
        parser = PokerResponseParser(action_parser=custom_parser)

        response = "ACTION: fold"
        result = parser.parse_response(response, preflop_actions)

        assert isinstance(result, ParseSuccess)

    def test_accepts_custom_narration_parser(self, preflop_actions):
        custom_parser = ThoughtProcessNarrationParser()
        parser = PokerResponseParser(narration_parser=custom_parser)

        response = "ACTION: fold"
        result = parser.parse_response(response, preflop_actions)

        assert isinstance(result, ParseSuccess)


class TestNarrationTrimming:
    """Tests for narration word limit trimming behavior."""

    def test_narration_exceeding_limit_gets_trimmed(
        self, parser, preflop_actions
    ):
        # THOUGHT_PROCESS has 1000 word limit
        sentence1 = " ".join(["word"] * 400) + "."
        sentence2 = " ".join(["word"] * 400) + "."
        sentence3 = (
            " ".join(["word"] * 400) + "."
        )  # Total ~1200, should get trimmed
        over_limit = f"{sentence1} {sentence2} {sentence3}"

        response = f"""
THOUGHT_PROCESS:
{over_limit}

ACTION: raise 300
"""
        result = parser.parse_response(response, preflop_actions)

        assert isinstance(result, ParseSuccess)
        assert isinstance(result.narration, Narration)
        assert len(result.narration.thought_process.split()) <= 1000

    def test_narration_within_limit_preserved(self, parser, preflop_actions):
        short_thought = " ".join(["word"] * 400) + "."

        response = f"""
THOUGHT_PROCESS:
{short_thought}

ACTION: raise 300
"""
        result = parser.parse_response(response, preflop_actions)

        assert isinstance(result, ParseSuccess)
        assert isinstance(result.narration, Narration)


class TestWhitespaceHandling:
    """Tests for whitespace handling in parsed content."""

    def test_extra_whitespace_cleaned_in_narration(
        self, parser, preflop_actions
    ):
        response = """
THOUGHT_PROCESS:
Mid-tournament,    37BB    stack.   This is  an excellent spot.

ACTION: raise 300
"""
        result = parser.parse_response(response, preflop_actions)

        assert isinstance(result, ParseSuccess)
        assert isinstance(result.narration, Narration)
        assert "37BB stack" in result.narration.thought_process
        assert "    " not in result.narration.thought_process


class TestCaseInsensitivity:
    """Tests for case-insensitive parsing."""

    def test_lowercase_field_names_work(self, parser, preflop_actions):
        response = """
thought_process:
Mid-tournament position play.

action: raise 300
"""
        result = parser.parse_response(response, preflop_actions)

        assert isinstance(result, ParseSuccess)
        assert isinstance(result.narration, Narration)
