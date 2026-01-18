"""Tests for PokerActionParser behavior and edge cases."""

import pytest

from src.application.poker.parser.action_parser import PokerActionParser
from src.application.protocols.response import ParseError, ParseErrorType
from src.domain.models.actions import Action, ActionType
from src.domain.models.available_action import AvailableRaiseAction
from src.domain.models.chips import ChipAmount


@pytest.fixture
def parser():
    return PokerActionParser()


class TestActionExtraction:
    """Tests for extracting actions from response text."""

    def test_extracts_fold(self, parser, preflop_actions):
        response = "ACTION: fold"
        result = parser.parse(response, preflop_actions)

        assert isinstance(result, Action)
        assert result.action_type == ActionType.FOLD

    def test_extracts_check(self, parser, postflop_actions):
        response = "ACTION: check"
        result = parser.parse(response, postflop_actions)

        assert isinstance(result, Action)
        assert result.action_type == ActionType.CHECK

    def test_extracts_call(self, parser, preflop_actions):
        response = "ACTION: call"
        result = parser.parse(response, preflop_actions)

        assert isinstance(result, Action)
        assert result.action_type == ActionType.CALL

    def test_extracts_bet_with_amount(self, parser, postflop_actions):
        response = "ACTION: bet 500"
        result = parser.parse(response, postflop_actions)

        assert isinstance(result, Action)
        assert result.action_type == ActionType.BET
        assert result.amount is not None
        assert result.amount.value == 500

    def test_extracts_raise_with_amount(self, parser, preflop_actions):
        response = "ACTION: raise 400"
        result = parser.parse(response, preflop_actions)

        assert isinstance(result, Action)
        assert result.action_type == ActionType.RAISE
        assert result.amount is not None
        assert result.amount.value == 400

    def test_extracts_all_in(self, parser, facing_bet_actions):
        response = "ACTION: all_in"
        result = parser.parse(response, facing_bet_actions)

        assert isinstance(result, Action)
        assert result.action_type == ActionType.ALL_IN
        assert result.amount is not None
        assert result.amount.value == 5000


class TestActionCaseInsensitivity:
    """Tests for case-insensitive action parsing."""

    def test_uppercase_action(self, parser, preflop_actions):
        response = "ACTION: FOLD"
        result = parser.parse(response, preflop_actions)
        assert isinstance(result, Action)
        assert result.action_type == ActionType.FOLD

    def test_mixed_case_action(self, parser, preflop_actions):
        response = "ACTION: RaIsE 500"
        result = parser.parse(response, preflop_actions)
        assert isinstance(result, Action)
        assert result.action_type == ActionType.RAISE

    def test_lowercase_action_label(self, parser, preflop_actions):
        response = "action: fold"
        result = parser.parse(response, preflop_actions)
        assert isinstance(result, Action)
        assert result.action_type == ActionType.FOLD


class TestAllInVariants:
    """Tests for all-in action format variants."""

    def test_allin_no_hyphen(self, parser, facing_bet_actions):
        response = "ACTION: allin"
        result = parser.parse(response, facing_bet_actions)
        assert isinstance(result, Action)
        assert result.action_type == ActionType.ALL_IN

    def test_all_in_with_hyphen(self, parser, facing_bet_actions):
        response = "ACTION: all-in"
        result = parser.parse(response, facing_bet_actions)
        assert isinstance(result, Action)
        assert result.action_type == ActionType.ALL_IN

    def test_all_in_with_underscore(self, parser, facing_bet_actions):
        response = "ACTION: all_in"
        result = parser.parse(response, facing_bet_actions)
        assert isinstance(result, Action)
        assert result.action_type == ActionType.ALL_IN


class TestAmountValidation:
    """Tests for bet/raise amount validation."""

    def test_raise_below_minimum_returns_error(self, parser, preflop_actions):
        response = "ACTION: raise 100"  # min is 200
        result = parser.parse(response, preflop_actions)

        assert isinstance(result, ParseError)
        assert result.error_type == ParseErrorType.AMOUNT_BELOW_MIN.value
        assert "100" in result.message

    def test_raise_above_maximum_returns_error(self, parser, preflop_actions):
        response = "ACTION: raise 5000"  # max is 2000
        result = parser.parse(response, preflop_actions)

        assert isinstance(result, ParseError)
        assert result.error_type == ParseErrorType.AMOUNT_ABOVE_MAX.value
        assert "5000" in result.message

    def test_bet_below_minimum_returns_error(self, parser, postflop_actions):
        response = "ACTION: bet 50"  # min is 100
        result = parser.parse(response, postflop_actions)

        assert isinstance(result, ParseError)
        assert result.error_type == ParseErrorType.AMOUNT_BELOW_MIN.value

    def test_bet_above_maximum_returns_error(self, parser, postflop_actions):
        response = "ACTION: bet 2000"  # max is 1000
        result = parser.parse(response, postflop_actions)

        assert isinstance(result, ParseError)
        assert result.error_type == ParseErrorType.AMOUNT_ABOVE_MAX.value

    def test_raise_at_minimum_succeeds(self, parser, preflop_actions):
        response = "ACTION: raise 200"  # min is 200
        result = parser.parse(response, preflop_actions)

        assert isinstance(result, Action)
        assert result.amount is not None
        assert result.amount.value == 200

    def test_raise_at_maximum_succeeds(self, parser, preflop_actions):
        response = "ACTION: raise 2000"  # max is 2000
        result = parser.parse(response, preflop_actions)

        assert isinstance(result, Action)
        assert result.amount is not None
        assert result.amount.value == 2000


class TestDefaultAmounts:
    """Tests for default amounts when not specified."""

    def test_raise_without_amount_uses_minimum(self, parser, preflop_actions):
        response = "ACTION: raise"
        result = parser.parse(response, preflop_actions)

        assert isinstance(result, Action)
        assert result.action_type == ActionType.RAISE
        assert result.amount is not None
        assert result.amount.value == 200  # min_raise_amount

    def test_bet_without_amount_uses_minimum(self, parser, postflop_actions):
        response = "ACTION: bet"
        result = parser.parse(response, postflop_actions)

        assert isinstance(result, Action)
        assert result.action_type == ActionType.BET
        assert result.amount is not None
        assert result.amount.value == 100  # min_bet_amount


class TestActionNotAvailable:
    """Tests for unavailable action handling."""

    def test_check_not_available_when_facing_bet(self, parser, preflop_actions):
        response = "ACTION: check"
        result = parser.parse(response, preflop_actions)

        assert isinstance(result, ParseError)
        assert result.error_type == ParseErrorType.ACTION_NOT_AVAILABLE.value
        assert "check" in result.message.lower()

    def test_bet_not_available_when_facing_bet(self, parser, preflop_actions):
        response = "ACTION: bet 100"
        result = parser.parse(response, preflop_actions)

        assert isinstance(result, ParseError)
        assert result.error_type == ParseErrorType.ACTION_NOT_AVAILABLE.value


class TestNoActionFound:
    """Tests for missing or malformed action patterns."""

    def test_no_action_keyword(self, parser, preflop_actions):
        response = "I think I should fold here."
        result = parser.parse(response, preflop_actions)

        assert isinstance(result, ParseError)
        assert result.error_type == ParseErrorType.NO_ACTION_FOUND.value

    def test_empty_response(self, parser, preflop_actions):
        response = ""
        result = parser.parse(response, preflop_actions)

        assert isinstance(result, ParseError)
        assert result.error_type == ParseErrorType.NO_ACTION_FOUND.value

    def test_malformed_action_line(self, parser, preflop_actions):
        response = "ACTION fold"  # Missing colon
        result = parser.parse(response, preflop_actions)

        assert isinstance(result, ParseError)

    def test_action_with_invalid_type(self, parser, preflop_actions):
        response = "ACTION: bluff"
        result = parser.parse(response, preflop_actions)

        assert isinstance(result, ParseError)


class TestWhitespaceHandling:
    """Tests for whitespace tolerance in parsing."""

    def test_extra_spaces_after_colon(self, parser, preflop_actions):
        response = "ACTION:    fold"
        result = parser.parse(response, preflop_actions)
        assert isinstance(result, Action)
        assert result.action_type == ActionType.FOLD

    def test_extra_spaces_before_amount(self, parser, preflop_actions):
        response = "ACTION: raise    500"
        result = parser.parse(response, preflop_actions)
        assert isinstance(result, Action)
        assert result.amount is not None
        assert result.amount.value == 500

    def test_action_in_middle_of_text(self, parser, preflop_actions):
        response = """
        After careful consideration...

        ACTION: fold

        This is the best play.
        """
        result = parser.parse(response, preflop_actions)
        assert isinstance(result, Action)
        assert result.action_type == ActionType.FOLD


class TestErrorContext:
    """Tests for error context information."""

    def test_amount_error_includes_context(self, parser):
        actions = [
            AvailableRaiseAction(
                min_raise_amount=ChipAmount(200),
                max_raise_amount=ChipAmount(1000),
            )
        ]
        response = "ACTION: raise 100"
        result = parser.parse(response, actions)

        assert isinstance(result, ParseError)
        assert result.context is not None
        assert result.context["requested_amount"] == 100
        assert result.context["min_raise_amount"] == 200
        assert result.context["max_raise_amount"] == 1000

    def test_unavailable_action_includes_available_types(self, parser, preflop_actions):
        response = "ACTION: check"
        result = parser.parse(response, preflop_actions)

        assert isinstance(result, ParseError)
        assert result.context is not None
        assert "available_action_types" in result.context
        assert "fold" in result.context["available_action_types"]

    def test_no_action_includes_response_snippet(self, parser, preflop_actions):
        long_response = "x" * 300
        result = parser.parse(long_response, preflop_actions)

        assert isinstance(result, ParseError)
        assert result.context is not None
        assert "response_snippet" in result.context
        assert len(result.context["response_snippet"]) <= 200
