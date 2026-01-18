"""Tests for StructuredNarrationParser behavior and edge cases."""

import pytest

from src.application.poker.parser.narration_parser import \
    StructuredNarrationParser
from src.application.protocols.response import ParseError
from src.domain.models.narration import Narration


@pytest.fixture
def parser():
    return StructuredNarrationParser()


class TestNarrationExtraction:
    """Tests for extracting complete narration from response."""

    def test_extracts_all_nine_fields(self, parser, full_narration_response):
        result = parser.parse(full_narration_response)

        assert isinstance(result, Narration)
        assert "Mid-tournament" in result.game_stage_assessment
        assert "Button position" in result.positional_context
        assert "UTG range" in result.range_analysis
        assert "TPTK" in result.equity_assessment
        assert "Alice plays" in result.opponent_modeling
        assert "3x raise" in result.bet_sizing_rationale
        assert "60% pot" in result.multi_street_plan
        assert "table image" in result.meta_considerations
        assert "Raise for value" in result.final_decision

    def test_returns_narration_object_type(self, parser, full_narration_response):
        result = parser.parse(full_narration_response)

        assert isinstance(result, Narration)
        assert hasattr(result, "game_stage_assessment")
        assert hasattr(result, "positional_context")
        assert hasattr(result, "final_decision")


class TestMissingFields:
    """Tests for handling missing narration fields."""

    def test_missing_first_field_returns_error(self, parser):
        response = """
POSITIONAL_CONTEXT:
Button position.

RANGE_ANALYSIS:
UTG range.

EQUITY_ASSESSMENT:
70% equity.

OPPONENT_MODELING:
Plays tight.

BET_SIZING_RATIONALE:
Standard sizing.

MULTI_STREET_PLAN:
Bet turn.

META_CONSIDERATIONS:
Table image.

FINAL_DECISION:
Raise for value.
"""
        result = parser.parse(response)

        assert isinstance(result, ParseError)
        assert "game_stage_assessment" in result.message.lower()

    def test_missing_middle_field_returns_error(self, parser):
        response = """
GAME_STAGE_ASSESSMENT:
Mid-tournament.

POSITIONAL_CONTEXT:
Button position.

RANGE_ANALYSIS:
UTG range.

OPPONENT_MODELING:
Plays tight.

BET_SIZING_RATIONALE:
Standard sizing.

MULTI_STREET_PLAN:
Bet turn.

META_CONSIDERATIONS:
Table image.

FINAL_DECISION:
Raise for value.
"""
        result = parser.parse(response)

        assert isinstance(result, ParseError)
        assert "equity_assessment" in result.message.lower()

    def test_missing_last_field_returns_error(self, parser):
        response = """
GAME_STAGE_ASSESSMENT:
Mid-tournament.

POSITIONAL_CONTEXT:
Button position.

RANGE_ANALYSIS:
UTG range.

EQUITY_ASSESSMENT:
70% equity.

OPPONENT_MODELING:
Plays tight.

BET_SIZING_RATIONALE:
Standard sizing.

MULTI_STREET_PLAN:
Bet turn.

META_CONSIDERATIONS:
Table image.
"""
        result = parser.parse(response)

        assert isinstance(result, ParseError)
        assert "final_decision" in result.message.lower()


class TestCaseInsensitivity:
    """Tests for case-insensitive field name parsing."""

    def test_lowercase_field_names(self, parser):
        response = """
game_stage_assessment:
Mid-tournament.

positional_context:
Button position.

range_analysis:
UTG range.

equity_assessment:
70% equity.

opponent_modeling:
Plays tight.

bet_sizing_rationale:
Standard sizing.

multi_street_plan:
Bet turn.

meta_considerations:
Table image.

final_decision:
Raise for value.

ACTION: fold
"""
        result = parser.parse(response)

        assert isinstance(result, Narration)

    def test_mixed_case_field_names(self, parser):
        response = """
Game_Stage_Assessment:
Mid-tournament.

Positional_Context:
Button position.

Range_Analysis:
UTG range.

Equity_Assessment:
70% equity.

Opponent_Modeling:
Plays tight.

Bet_Sizing_Rationale:
Standard sizing.

Multi_Street_Plan:
Bet turn.

Meta_Considerations:
Table image.

Final_Decision:
Raise for value.

ACTION: fold
"""
        result = parser.parse(response)

        assert isinstance(result, Narration)


class TestWordLimitTrimming:
    """Tests for word limit enforcement and trimming."""

    def test_field_within_limit_passes(self, parser):
        short_content = "This is a short assessment."
        response = f"""
GAME_STAGE_ASSESSMENT:
{short_content}

POSITIONAL_CONTEXT:
Button position.

RANGE_ANALYSIS:
UTG range.

EQUITY_ASSESSMENT:
70% equity.

OPPONENT_MODELING:
Plays tight.

BET_SIZING_RATIONALE:
Standard sizing.

MULTI_STREET_PLAN:
Bet turn.

META_CONSIDERATIONS:
Table image.

FINAL_DECISION:
Raise for value.
"""
        result = parser.parse(response)

        assert isinstance(result, Narration)
        assert short_content in result.game_stage_assessment

    def test_field_over_limit_gets_trimmed(self, parser):
        # final_decision has 60 word limit (50 + 20%)
        # Create content with multiple sentences, one of which pushes over limit
        sentence1 = " ".join(["word"] * 20) + "."
        sentence2 = " ".join(["word"] * 25) + "."
        sentence3 = " ".join(["word"] * 30) + "."  # This should get trimmed
        over_limit_content = f"{sentence1} {sentence2} {sentence3}"

        response = f"""
GAME_STAGE_ASSESSMENT:
Mid-tournament.

POSITIONAL_CONTEXT:
Button position.

RANGE_ANALYSIS:
UTG range.

EQUITY_ASSESSMENT:
70% equity.

OPPONENT_MODELING:
Plays tight.

BET_SIZING_RATIONALE:
Standard sizing.

MULTI_STREET_PLAN:
Bet turn.

META_CONSIDERATIONS:
Table image.

FINAL_DECISION:
{over_limit_content}

ACTION: fold
"""
        result = parser.parse(response)

        assert isinstance(result, Narration)
        assert len(result.final_decision.split()) <= 60
        assert len(result.final_decision.split()) < 75  # Confirms trimming occurred

    def test_single_long_sentence_trimmed_to_empty_returns_error(self, parser):
        # A single sentence with 100+ words that exceeds limit
        # When trimmed, nothing remains
        single_long_sentence = " ".join(["word"] * 100)

        response = f"""
GAME_STAGE_ASSESSMENT:
Mid-tournament.

POSITIONAL_CONTEXT:
Button position.

RANGE_ANALYSIS:
UTG range.

EQUITY_ASSESSMENT:
70% equity.

OPPONENT_MODELING:
Plays tight.

BET_SIZING_RATIONALE:
Standard sizing.

MULTI_STREET_PLAN:
Bet turn.

META_CONSIDERATIONS:
Table image.

FINAL_DECISION:
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
GAME_STAGE_ASSESSMENT:
Mid-tournament,    37BB    stack,     no pressure.

POSITIONAL_CONTEXT:
Button position.

RANGE_ANALYSIS:
UTG range.

EQUITY_ASSESSMENT:
70% equity.

OPPONENT_MODELING:
Plays tight.

BET_SIZING_RATIONALE:
Standard sizing.

MULTI_STREET_PLAN:
Bet turn.

META_CONSIDERATIONS:
Table image.

FINAL_DECISION:
Raise for value.
"""
        result = parser.parse(response)

        assert isinstance(result, Narration)
        assert "37BB stack" in result.game_stage_assessment
        assert "    " not in result.game_stage_assessment

    def test_preserves_single_paragraph_breaks(self, parser):
        response = """
GAME_STAGE_ASSESSMENT:
First paragraph.

Second paragraph.

POSITIONAL_CONTEXT:
Button position.

RANGE_ANALYSIS:
UTG range.

EQUITY_ASSESSMENT:
70% equity.

OPPONENT_MODELING:
Plays tight.

BET_SIZING_RATIONALE:
Standard sizing.

MULTI_STREET_PLAN:
Bet turn.

META_CONSIDERATIONS:
Table image.

FINAL_DECISION:
Raise for value.
"""
        result = parser.parse(response)

        assert isinstance(result, Narration)


class TestMinimalValidResponse:
    """Tests for responses without narration."""

    def test_action_only_response_returns_error(self, parser):
        response = """
ACTION: fold

REASONING:
Hand is too weak.
"""
        result = parser.parse(response)

        assert isinstance(result, ParseError)


class TestErrorContext:
    """Tests for error context information."""

    def test_missing_field_error_includes_field_name(self, parser):
        response = """
GAME_STAGE_ASSESSMENT:
Mid-tournament.
"""
        result = parser.parse(response)

        assert isinstance(result, ParseError)
        assert result.context is not None
        assert "missing_field" in result.context

    def test_error_includes_response_snippet(self, parser):
        long_response = "GAME_STAGE_ASSESSMENT:\n" + "x" * 300

        result = parser.parse(long_response)

        assert isinstance(result, ParseError)
        assert result.context is not None
        assert "response_snippet" in result.context
        assert len(result.context["response_snippet"]) <= 200
