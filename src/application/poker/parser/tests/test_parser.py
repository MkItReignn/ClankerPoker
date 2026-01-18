"""Tests for PokerResponseParser composition and behavior."""

import pytest

from src.application.poker.parser.action_parser import PokerActionParser
from src.application.poker.parser.narration_parser import \
    StructuredNarrationParser
from src.application.poker.parser.parser import PokerResponseParser
from src.application.poker.parser.reasoning_parser import RegexReasoningParser
from src.application.protocols.response import (ParseError, ParseErrorType,
                                                ParseFailure, ParseSuccess)
from src.domain.models.actions import ActionType
from src.domain.models.available_action import (AvailableCallAction,
                                                AvailableCheckAction,
                                                AvailableFoldAction)
from src.domain.models.chips import ChipAmount
from src.domain.models.narration import Narration


@pytest.fixture
def parser():
    return PokerResponseParser()


class TestParseResponseSuccess:
    """Tests for successful response parsing."""

    def test_parses_full_response_with_narration(
        self, parser, full_narration_response, preflop_actions
    ):
        result = parser.parse_response(full_narration_response, preflop_actions)

        assert isinstance(result, ParseSuccess)
        assert result.action.action_type == ActionType.RAISE
        assert result.action.amount.value == 300
        assert isinstance(result.narration, Narration)
        assert isinstance(result.reasoning, str)

    def test_parses_minimal_response(self, parser, minimal_response, preflop_actions):
        result = parser.parse_response(minimal_response, preflop_actions)

        assert isinstance(result, ParseSuccess)
        assert result.action.action_type == ActionType.FOLD
        assert isinstance(result.narration, ParseError)
        assert isinstance(result.reasoning, str)
        assert "too weak" in result.reasoning


class TestBackwardCompatibility:
    """Tests for backward compatibility with old response formats."""

    def test_action_and_reasoning_only_still_works(self, parser, preflop_actions):
        response = """
ACTION: raise 500

REASONING:
Value raise with position and range advantage.
"""
        result = parser.parse_response(response, preflop_actions)

        assert isinstance(result, ParseSuccess)
        assert result.action.action_type == ActionType.RAISE
        assert isinstance(result.narration, ParseError)
        assert isinstance(result.reasoning, str)
        assert "Value raise" in result.reasoning

    def test_action_only_still_works(self, parser, preflop_actions):
        response = "ACTION: fold"
        result = parser.parse_response(response, preflop_actions)

        assert isinstance(result, ParseSuccess)
        assert result.action.action_type == ActionType.FOLD
        assert isinstance(result.narration, ParseError)
        assert isinstance(result.reasoning, ParseError)


class TestNarrationOptional:
    """Tests demonstrating narration is optional for success."""

    def test_missing_narration_fields_still_succeeds(self, parser, preflop_actions):
        response = """
GAME_STAGE_ASSESSMENT:
Mid-tournament.

POSITIONAL_CONTEXT:
Button position.

ACTION: raise 300

REASONING:
Value raise.
"""
        result = parser.parse_response(response, preflop_actions)

        assert isinstance(result, ParseSuccess)
        assert isinstance(result.narration, ParseError)  # Incomplete narration returns error

    def test_empty_narration_field_still_succeeds(self, parser, preflop_actions):
        response = """
GAME_STAGE_ASSESSMENT:

ACTION: fold

REASONING:
Too weak.
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
        assert result.error.error_type == ParseErrorType.ACTION_NOT_AVAILABLE.value


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
        custom_parser = StructuredNarrationParser()
        parser = PokerResponseParser(narration_parser=custom_parser)

        response = "ACTION: fold"
        result = parser.parse_response(response, preflop_actions)

        assert isinstance(result, ParseSuccess)

    def test_accepts_custom_reasoning_parser(self, preflop_actions):
        custom_parser = RegexReasoningParser()
        parser = PokerResponseParser(reasoning_parser=custom_parser)

        response = "ACTION: fold\n\nREASONING: Hand is weak."
        result = parser.parse_response(response, preflop_actions)

        assert isinstance(result, ParseSuccess)
        assert isinstance(result.reasoning, str)


class TestNarrationTrimming:
    """Tests for narration word limit trimming behavior."""

    def test_narration_exceeding_limit_gets_trimmed(self, parser, preflop_actions):
        # FINAL_DECISION has 60 word limit
        sentence1 = " ".join(["word"] * 20) + "."
        sentence2 = " ".join(["word"] * 25) + "."
        sentence3 = " ".join(["word"] * 30) + "."  # Should get trimmed
        over_limit = f"{sentence1} {sentence2} {sentence3}"

        response = f"""
GAME_STAGE_ASSESSMENT:
Mid-tournament, 37BB stack.

POSITIONAL_CONTEXT:
Button position, good odds.

RANGE_ANALYSIS:
Opponent has wide range.

EQUITY_ASSESSMENT:
70% equity against range.

OPPONENT_MODELING:
Plays straightforward.

BET_SIZING_RATIONALE:
Standard 3x sizing.

MULTI_STREET_PLAN:
Continue betting turns.

META_CONSIDERATIONS:
Building table image.

FINAL_DECISION:
{over_limit}

ACTION: raise 300

REASONING:
Value raise.
"""
        result = parser.parse_response(response, preflop_actions)

        assert isinstance(result, ParseSuccess)
        assert isinstance(result.narration, Narration)
        assert len(result.narration.final_decision.split()) <= 60

    def test_narration_within_limit_preserved(self, parser, preflop_actions):
        short_decision = " ".join(["word"] * 40) + "."

        response = f"""
GAME_STAGE_ASSESSMENT:
Mid-tournament, 37BB stack.

POSITIONAL_CONTEXT:
Button position, good odds.

RANGE_ANALYSIS:
Opponent has wide range.

EQUITY_ASSESSMENT:
70% equity against range.

OPPONENT_MODELING:
Plays straightforward.

BET_SIZING_RATIONALE:
Standard 3x sizing.

MULTI_STREET_PLAN:
Continue betting turns.

META_CONSIDERATIONS:
Building table image.

FINAL_DECISION:
{short_decision}

ACTION: raise 300

REASONING:
Value raise.
"""
        result = parser.parse_response(response, preflop_actions)

        assert isinstance(result, ParseSuccess)
        assert isinstance(result.narration, Narration)


class TestWhitespaceHandling:
    """Tests for whitespace handling in parsed content."""

    def test_extra_whitespace_cleaned_in_narration(self, parser, preflop_actions):
        response = """
GAME_STAGE_ASSESSMENT:
Mid-tournament,    37BB    stack.

POSITIONAL_CONTEXT:
Button position.

RANGE_ANALYSIS:
Opponent range.

EQUITY_ASSESSMENT:
70% equity.

OPPONENT_MODELING:
Plays tight.

BET_SIZING_RATIONALE:
Standard sizing.

MULTI_STREET_PLAN:
Bet turns.

META_CONSIDERATIONS:
Table image.

FINAL_DECISION:
Raise for value.

ACTION: raise 300

REASONING:
Value raise.
"""
        result = parser.parse_response(response, preflop_actions)

        assert isinstance(result, ParseSuccess)
        assert isinstance(result.narration, Narration)
        assert "37BB stack" in result.narration.game_stage_assessment
        assert "    " not in result.narration.game_stage_assessment


class TestCaseInsensitivity:
    """Tests for case-insensitive parsing."""

    def test_lowercase_field_names_work(self, parser, preflop_actions):
        response = """
game_stage_assessment:
Mid-tournament.

positional_context:
Button position.

range_analysis:
Opponent range.

equity_assessment:
70% equity.

opponent_modeling:
Plays tight.

bet_sizing_rationale:
Standard sizing.

multi_street_plan:
Bet turns.

meta_considerations:
Table image.

final_decision:
Raise for value.

action: raise 300

reasoning:
Value raise.
"""
        result = parser.parse_response(response, preflop_actions)

        assert isinstance(result, ParseSuccess)
        assert isinstance(result.narration, Narration)
        assert isinstance(result.reasoning, str)
