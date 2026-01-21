"""Tests for RecordToLlmContextSerializer.

Tests verify output matches the notation defined in config/poker/prompts.yaml:
- Action shorthand: F=Fold, X=Check, C=Call, B<amt>=Bet, R<amt>=Raise, AI<amt>=All-in
- Position abbreviations: BTN, SB, BB, UTG, UTG+1, CO
- Viewer perspective: "you" for viewer_id, player names for others
- Current phase marker: "?" indicates decision point
- Previous hands format: H<n>: Winner=<name>, Pot=<amount>, Showdown=<yes|no>
"""

from __future__ import annotations

from src.application.poker.records.context_serializer import \
    RecordToLlmContextSerializer
from src.application.poker.records.context_serializer.tests.conftest import (
    make_game_record, make_hand_level_player_record, make_hand_outcome,
    make_hand_record, make_round_level_player_record, make_round_record,
    make_showdown_result, make_turn_record)
from src.application.poker.records.models import PlayerOutcome
from src.domain.models.actions import ActionType
from src.domain.models.card import Card, Rank, Suit
from src.domain.models.chips import ChipAmount
from src.domain.models.game import GamePhase
from src.domain.models.hand import Hand
from src.domain.models.position import PositionName
from src.domain.models.seat import Seat


class TestActionNotation:
    """Tests for action shorthand notation per prompts.yaml."""

    def test_fold_serializes_as_f(self, default_game_metadata):
        """Fold action serializes as 'F'."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Alice", Seat.SEAT_0, PositionName.BUTTON),
        }
        round_records = {
            "p1": make_round_level_player_record("p1", "Alice", Seat.SEAT_0),
        }
        turn = make_turn_record("p1", "Alice", Seat.SEAT_0, ActionType.FOLD)
        round_record = make_round_record(GamePhase.PRE_FLOP, round_records, [turn])
        hand = make_hand_record(1, player_records, [round_record])

        result = RecordToLlmContextSerializer.serialize_current_hand_actions(hand, "pre_flop")

        assert "Alice(BTN):F" in result

    def test_check_serializes_as_x(self, default_game_metadata):
        """Check action serializes as 'X'."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Bob", Seat.SEAT_1, PositionName.BIG_BLIND),
        }
        round_records = {
            "p1": make_round_level_player_record("p1", "Bob", Seat.SEAT_1),
        }
        turn = make_turn_record("p1", "Bob", Seat.SEAT_1, ActionType.CHECK, phase=GamePhase.FLOP)
        round_record = make_round_record(GamePhase.FLOP, round_records, [turn])
        hand = make_hand_record(1, player_records, [round_record])

        result = RecordToLlmContextSerializer.serialize_current_hand_actions(hand, "flop")

        assert "Bob(BB):X" in result

    def test_call_serializes_as_c(self, default_game_metadata):
        """Call action serializes as 'C' without amount."""
        player_records = {
            "p1": make_hand_level_player_record(
                "p1", "Carol", Seat.SEAT_2, PositionName.SMALL_BLIND
            ),
        }
        round_records = {
            "p1": make_round_level_player_record("p1", "Carol", Seat.SEAT_2),
        }
        turn = make_turn_record("p1", "Carol", Seat.SEAT_2, ActionType.CALL)
        round_record = make_round_record(GamePhase.PRE_FLOP, round_records, [turn])
        hand = make_hand_record(1, player_records, [round_record])

        result = RecordToLlmContextSerializer.serialize_current_hand_actions(hand, "pre_flop")

        assert "Carol(SB):C" in result

    def test_bet_serializes_as_b_with_amount(self, default_game_metadata):
        """Bet action serializes as 'B<amount>'."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Dave", Seat.SEAT_0, PositionName.BUTTON),
        }
        round_records = {
            "p1": make_round_level_player_record("p1", "Dave", Seat.SEAT_0),
        }
        turn = make_turn_record(
            "p1", "Dave", Seat.SEAT_0, ActionType.BET, amount=100, phase=GamePhase.FLOP
        )
        round_record = make_round_record(GamePhase.FLOP, round_records, [turn])
        hand = make_hand_record(1, player_records, [round_record])

        result = RecordToLlmContextSerializer.serialize_current_hand_actions(hand, "flop")

        assert "Dave(BTN):B100" in result

    def test_raise_serializes_as_r_with_amount(self, default_game_metadata):
        """Raise action serializes as 'R<amount>' (total bet amount)."""
        player_records = {
            "p1": make_hand_level_player_record(
                "p1", "Eve", Seat.SEAT_3, PositionName.UNDER_THE_GUN
            ),
        }
        round_records = {
            "p1": make_round_level_player_record("p1", "Eve", Seat.SEAT_3),
        }
        turn = make_turn_record("p1", "Eve", Seat.SEAT_3, ActionType.RAISE, amount=200)
        round_record = make_round_record(GamePhase.PRE_FLOP, round_records, [turn])
        hand = make_hand_record(1, player_records, [round_record])

        result = RecordToLlmContextSerializer.serialize_current_hand_actions(hand, "pre_flop")

        assert "Eve(UTG):R200" in result

    def test_all_in_serializes_as_ai_with_amount(self, default_game_metadata):
        """All-in action serializes as 'AI<amount>'."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Frank", Seat.SEAT_4, PositionName.CUTOFF),
        }
        round_records = {
            "p1": make_round_level_player_record("p1", "Frank", Seat.SEAT_4),
        }
        turn = make_turn_record("p1", "Frank", Seat.SEAT_4, ActionType.ALL_IN, amount=500)
        round_record = make_round_record(GamePhase.PRE_FLOP, round_records, [turn])
        hand = make_hand_record(1, player_records, [round_record])

        result = RecordToLlmContextSerializer.serialize_current_hand_actions(hand, "pre_flop")

        assert "Frank(CO):AI500" in result


class TestPositionAbbreviations:
    """Tests for position shorthand notation per prompts.yaml."""

    def test_button_serializes_as_btn(self, default_game_metadata):
        """Button position serializes as 'BTN'."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Alice", Seat.SEAT_0, PositionName.BUTTON),
        }
        round_records = {
            "p1": make_round_level_player_record("p1", "Alice", Seat.SEAT_0),
        }
        turn = make_turn_record("p1", "Alice", Seat.SEAT_0, ActionType.FOLD)
        round_record = make_round_record(GamePhase.PRE_FLOP, round_records, [turn])
        hand = make_hand_record(1, player_records, [round_record])

        result = RecordToLlmContextSerializer.serialize_current_hand_actions(hand, "pre_flop")

        assert "(BTN)" in result

    def test_small_blind_serializes_as_sb(self, default_game_metadata):
        """Small blind position serializes as 'SB'."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Bob", Seat.SEAT_1, PositionName.SMALL_BLIND),
        }
        round_records = {
            "p1": make_round_level_player_record("p1", "Bob", Seat.SEAT_1),
        }
        turn = make_turn_record("p1", "Bob", Seat.SEAT_1, ActionType.CALL)
        round_record = make_round_record(GamePhase.PRE_FLOP, round_records, [turn])
        hand = make_hand_record(1, player_records, [round_record])

        result = RecordToLlmContextSerializer.serialize_current_hand_actions(hand, "pre_flop")

        assert "(SB)" in result

    def test_big_blind_serializes_as_bb(self, default_game_metadata):
        """Big blind position serializes as 'BB'."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Carol", Seat.SEAT_2, PositionName.BIG_BLIND),
        }
        round_records = {
            "p1": make_round_level_player_record("p1", "Carol", Seat.SEAT_2),
        }
        turn = make_turn_record("p1", "Carol", Seat.SEAT_2, ActionType.CHECK)
        round_record = make_round_record(GamePhase.FLOP, round_records, [turn])
        hand = make_hand_record(1, player_records, [round_record])

        result = RecordToLlmContextSerializer.serialize_current_hand_actions(hand, "flop")

        assert "(BB)" in result

    def test_utg_serializes_as_utg(self, default_game_metadata):
        """Under the gun position serializes as 'UTG'."""
        player_records = {
            "p1": make_hand_level_player_record(
                "p1", "Dave", Seat.SEAT_3, PositionName.UNDER_THE_GUN
            ),
        }
        round_records = {
            "p1": make_round_level_player_record("p1", "Dave", Seat.SEAT_3),
        }
        turn = make_turn_record("p1", "Dave", Seat.SEAT_3, ActionType.RAISE, amount=60)
        round_record = make_round_record(GamePhase.PRE_FLOP, round_records, [turn])
        hand = make_hand_record(1, player_records, [round_record])

        result = RecordToLlmContextSerializer.serialize_current_hand_actions(hand, "pre_flop")

        assert "(UTG)" in result

    def test_utg_plus_one_serializes_as_utg_plus_1(self, default_game_metadata):
        """UTG+1 position serializes as 'UTG+1'."""
        player_records = {
            "p1": make_hand_level_player_record(
                "p1", "Eve", Seat.SEAT_4, PositionName.UTG_PLUS_ONE
            ),
        }
        round_records = {
            "p1": make_round_level_player_record("p1", "Eve", Seat.SEAT_4),
        }
        turn = make_turn_record("p1", "Eve", Seat.SEAT_4, ActionType.CALL)
        round_record = make_round_record(GamePhase.PRE_FLOP, round_records, [turn])
        hand = make_hand_record(1, player_records, [round_record])

        result = RecordToLlmContextSerializer.serialize_current_hand_actions(hand, "pre_flop")

        assert "(UTG+1)" in result

    def test_cutoff_serializes_as_co(self, default_game_metadata):
        """Cutoff position serializes as 'CO'."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Frank", Seat.SEAT_5, PositionName.CUTOFF),
        }
        round_records = {
            "p1": make_round_level_player_record("p1", "Frank", Seat.SEAT_5),
        }
        turn = make_turn_record("p1", "Frank", Seat.SEAT_5, ActionType.FOLD)
        round_record = make_round_record(GamePhase.PRE_FLOP, round_records, [turn])
        hand = make_hand_record(1, player_records, [round_record])

        result = RecordToLlmContextSerializer.serialize_current_hand_actions(hand, "pre_flop")

        assert "(CO)" in result


class TestViewerPerspective:
    """Tests for viewer perspective (you vs player names)."""

    def test_viewer_player_appears_as_you_in_current_hand(self, default_game_metadata):
        """When viewer_id matches a player, their name appears as 'you'."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Alice", Seat.SEAT_0, PositionName.BUTTON),
            "p2": make_hand_level_player_record("p2", "Bob", Seat.SEAT_1, PositionName.SMALL_BLIND),
        }
        outcome = make_hand_outcome(
            winner_ids=("p1",),
            pot_amount=100,
            player_outcomes=(
                PlayerOutcome("p1", "Alice", ChipAmount(100), ChipAmount(1100)),
                PlayerOutcome("p2", "Bob", ChipAmount(0), ChipAmount(950)),
            ),
        )
        hand = make_hand_record(1, player_records, outcome=outcome)
        game = make_game_record("game1", default_game_metadata, [hand])

        result = RecordToLlmContextSerializer.serialize_recent_records(game, viewer_id="p1")

        assert "you(BTN)" in result
        assert "Alice(BTN)" not in result

    def test_non_viewer_players_use_their_names(self, default_game_metadata):
        """Non-viewer players appear with their actual names."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Alice", Seat.SEAT_0, PositionName.BUTTON),
            "p2": make_hand_level_player_record("p2", "Bob", Seat.SEAT_1, PositionName.SMALL_BLIND),
        }
        outcome = make_hand_outcome(
            winner_ids=("p1",),
            pot_amount=100,
            player_outcomes=(
                PlayerOutcome("p1", "Alice", ChipAmount(100), ChipAmount(1100)),
                PlayerOutcome("p2", "Bob", ChipAmount(0), ChipAmount(950)),
            ),
        )
        hand = make_hand_record(1, player_records, outcome=outcome)
        game = make_game_record("game1", default_game_metadata, [hand])

        result = RecordToLlmContextSerializer.serialize_recent_records(game, viewer_id="p1")

        assert "Bob(SB)" in result

    def test_no_viewer_id_shows_all_names(self, default_game_metadata):
        """When no viewer_id, all players appear with their actual names."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Alice", Seat.SEAT_0, PositionName.BUTTON),
            "p2": make_hand_level_player_record("p2", "Bob", Seat.SEAT_1, PositionName.SMALL_BLIND),
        }
        outcome = make_hand_outcome(
            winner_ids=("p1",),
            pot_amount=100,
            player_outcomes=(
                PlayerOutcome("p1", "Alice", ChipAmount(100), ChipAmount(1100)),
                PlayerOutcome("p2", "Bob", ChipAmount(0), ChipAmount(950)),
            ),
        )
        hand = make_hand_record(1, player_records, outcome=outcome)
        game = make_game_record("game1", default_game_metadata, [hand])

        result = RecordToLlmContextSerializer.serialize_recent_records(game, viewer_id=None)

        assert "Alice(BTN)" in result
        assert "Bob(SB)" in result
        assert "you" not in result

    def test_viewer_as_winner_shows_you_in_winner_field(self, default_game_metadata):
        """When viewer is winner, Winner field shows 'you'."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Alice", Seat.SEAT_0, PositionName.BUTTON),
            "p2": make_hand_level_player_record("p2", "Bob", Seat.SEAT_1, PositionName.SMALL_BLIND),
        }
        outcome = make_hand_outcome(
            winner_ids=("p1",),
            pot_amount=100,
            player_outcomes=(
                PlayerOutcome("p1", "Alice", ChipAmount(100), ChipAmount(1100)),
                PlayerOutcome("p2", "Bob", ChipAmount(0), ChipAmount(950)),
            ),
        )
        hand = make_hand_record(1, player_records, outcome=outcome)
        game = make_game_record("game1", default_game_metadata, [hand])

        result = RecordToLlmContextSerializer.serialize_recent_records(game, viewer_id="p1")

        assert "Winner=you" in result


class TestCurrentPhaseMarker:
    """Tests for current phase '?' marker."""

    def test_current_phase_with_no_actions_shows_question_mark(self, default_game_metadata):
        """Current phase with no actions shows just '?'."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Alice", Seat.SEAT_0, PositionName.BUTTON),
        }
        hand = make_hand_record(1, player_records, rounds=[])

        result = RecordToLlmContextSerializer.serialize_current_hand_actions(hand, "pre_flop")

        assert "PRE_FLOP: ?" in result

    def test_current_phase_with_actions_shows_question_mark_at_end(self, default_game_metadata):
        """Current phase with actions shows '?' after actions."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Alice", Seat.SEAT_0, PositionName.BUTTON),
            "p2": make_hand_level_player_record("p2", "Bob", Seat.SEAT_1, PositionName.SMALL_BLIND),
        }
        round_records = {
            "p1": make_round_level_player_record("p1", "Alice", Seat.SEAT_0),
            "p2": make_round_level_player_record("p2", "Bob", Seat.SEAT_1),
        }
        turn = make_turn_record("p1", "Alice", Seat.SEAT_0, ActionType.RAISE, amount=60)
        round_record = make_round_record(GamePhase.PRE_FLOP, round_records, [turn])
        hand = make_hand_record(1, player_records, [round_record])

        result = RecordToLlmContextSerializer.serialize_current_hand_actions(hand, "pre_flop")

        assert "PRE_FLOP: Alice(BTN):R60, ?" in result

    def test_previous_phases_do_not_show_question_mark(self, default_game_metadata):
        """Phases before current phase don't show '?'."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Alice", Seat.SEAT_0, PositionName.BUTTON),
        }
        round_records = {
            "p1": make_round_level_player_record("p1", "Alice", Seat.SEAT_0),
        }
        preflop_turn = make_turn_record("p1", "Alice", Seat.SEAT_0, ActionType.RAISE, amount=60)
        preflop_round = make_round_record(GamePhase.PRE_FLOP, round_records, [preflop_turn])
        hand = make_hand_record(1, player_records, [preflop_round])

        result = RecordToLlmContextSerializer.serialize_current_hand_actions(hand, "flop")

        # PRE_FLOP should not have ? since we're on FLOP
        lines = result.strip().split("\n")
        preflop_line = next(line for line in lines if "PRE_FLOP:" in line)
        assert "?" not in preflop_line

    def test_new_phase_with_no_recorded_actions_shows_question_mark(self, default_game_metadata):
        """New current phase not yet in rounds list shows '?'."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Alice", Seat.SEAT_0, PositionName.BUTTON),
        }
        round_records = {
            "p1": make_round_level_player_record("p1", "Alice", Seat.SEAT_0),
        }
        preflop_turn = make_turn_record("p1", "Alice", Seat.SEAT_0, ActionType.CALL)
        preflop_round = make_round_record(GamePhase.PRE_FLOP, round_records, [preflop_turn])
        hand = make_hand_record(1, player_records, [preflop_round])

        result = RecordToLlmContextSerializer.serialize_current_hand_actions(hand, "flop")

        assert "FLOP: ?" in result


class TestPreviousHandsFormat:
    """Tests for previous hands serialization format."""

    def test_hand_summary_format_matches_spec(self, default_game_metadata):
        """Hand summary follows 'H<n>: Winner=<name>, Pot=<amount>, Showdown=<yes|no>'."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Alice", Seat.SEAT_0, PositionName.BUTTON),
            "p2": make_hand_level_player_record("p2", "Bob", Seat.SEAT_1, PositionName.SMALL_BLIND),
        }
        outcome = make_hand_outcome(
            winner_ids=("p1",),
            pot_amount=150,
            was_showdown=False,
            player_outcomes=(
                PlayerOutcome("p1", "Alice", ChipAmount(150), ChipAmount(1150)),
                PlayerOutcome("p2", "Bob", ChipAmount(0), ChipAmount(850)),
            ),
        )
        hand = make_hand_record(1, player_records, outcome=outcome)
        game = make_game_record("game1", default_game_metadata, [hand])

        result = RecordToLlmContextSerializer.serialize_recent_records(game)

        assert "H1: Winner=Alice, Pot=150, Showdown=no" in result

    def test_showdown_yes_when_was_showdown(self, default_game_metadata):
        """Showdown field shows 'yes' when hand went to showdown."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Alice", Seat.SEAT_0, PositionName.BUTTON),
            "p2": make_hand_level_player_record("p2", "Bob", Seat.SEAT_1, PositionName.SMALL_BLIND),
        }
        hole_cards_1 = Hand(Card(Suit.HEARTS, Rank.ACE), Card(Suit.SPADES, Rank.KING))
        hole_cards_2 = Hand(Card(Suit.DIAMONDS, Rank.QUEEN), Card(Suit.CLUBS, Rank.JACK))
        showdown_results = (
            make_showdown_result("p1", "Alice", hole_cards_1),
            make_showdown_result("p2", "Bob", hole_cards_2),
        )
        outcome = make_hand_outcome(
            winner_ids=("p1",),
            pot_amount=200,
            was_showdown=True,
            showdown_results=showdown_results,
            player_outcomes=(
                PlayerOutcome("p1", "Alice", ChipAmount(200), ChipAmount(1200)),
                PlayerOutcome("p2", "Bob", ChipAmount(0), ChipAmount(800)),
            ),
        )
        hand = make_hand_record(1, player_records, outcome=outcome)
        game = make_game_record("game1", default_game_metadata, [hand])

        result = RecordToLlmContextSerializer.serialize_recent_records(game)

        assert "Showdown=yes" in result

    def test_stacks_line_format(self, default_game_metadata):
        """Stacks line follows 'Stacks: <name>(<pos>)=<chips>, ...'."""
        player_records = {
            "p1": make_hand_level_player_record(
                "p1", "Alice", Seat.SEAT_0, PositionName.BUTTON, starting_chips=1500
            ),
            "p2": make_hand_level_player_record(
                "p2", "Bob", Seat.SEAT_1, PositionName.SMALL_BLIND, starting_chips=980
            ),
        }
        outcome = make_hand_outcome(
            winner_ids=("p1",),
            pot_amount=100,
            player_outcomes=(
                PlayerOutcome("p1", "Alice", ChipAmount(100), ChipAmount(1600)),
                PlayerOutcome("p2", "Bob", ChipAmount(0), ChipAmount(880)),
            ),
        )
        hand = make_hand_record(1, player_records, outcome=outcome)
        game = make_game_record("game1", default_game_metadata, [hand])

        result = RecordToLlmContextSerializer.serialize_recent_records(game)

        assert "Stacks:" in result
        assert "Alice(BTN)=1500" in result
        assert "Bob(SB)=980" in result

    def test_action_sequence_format(self, default_game_metadata):
        """Action sequence follows '<PHASE>: <name>(<pos>):<action>, ...'."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Alice", Seat.SEAT_0, PositionName.BUTTON),
            "p2": make_hand_level_player_record("p2", "Bob", Seat.SEAT_1, PositionName.SMALL_BLIND),
        }
        round_records = {
            "p1": make_round_level_player_record("p1", "Alice", Seat.SEAT_0),
            "p2": make_round_level_player_record("p2", "Bob", Seat.SEAT_1),
        }
        turns = [
            make_turn_record(
                "p1", "Alice", Seat.SEAT_0, ActionType.RAISE, amount=60, turn_number=1
            ),
            make_turn_record("p2", "Bob", Seat.SEAT_1, ActionType.CALL, turn_number=2),
        ]
        round_record = make_round_record(GamePhase.PRE_FLOP, round_records, turns)
        outcome = make_hand_outcome(
            winner_ids=("p1",),
            pot_amount=120,
            player_outcomes=(
                PlayerOutcome("p1", "Alice", ChipAmount(120), ChipAmount(1120)),
                PlayerOutcome("p2", "Bob", ChipAmount(0), ChipAmount(940)),
            ),
        )
        hand = make_hand_record(1, player_records, [round_record], outcome=outcome)
        game = make_game_record("game1", default_game_metadata, [hand])

        result = RecordToLlmContextSerializer.serialize_recent_records(game)

        assert "PRE_FLOP: Alice(BTN):R60, Bob(SB):C" in result

    def test_header_shows_previous_hands(self, default_game_metadata):
        """Output includes '=== PREVIOUS HANDS ===' header."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Alice", Seat.SEAT_0, PositionName.BUTTON),
        }
        outcome = make_hand_outcome(
            winner_ids=("p1",),
            pot_amount=100,
            player_outcomes=(PlayerOutcome("p1", "Alice", ChipAmount(100), ChipAmount(1100)),),
        )
        hand = make_hand_record(1, player_records, outcome=outcome)
        game = make_game_record("game1", default_game_metadata, [hand])

        result = RecordToLlmContextSerializer.serialize_recent_records(game)

        assert "=== PREVIOUS HANDS ===" in result


class TestEdgeCases:
    """Edge case tests."""

    def test_empty_game_record_returns_empty_string(self, default_game_metadata):
        """Game with no completed hands returns empty string."""
        game = make_game_record("game1", default_game_metadata, [])

        result = RecordToLlmContextSerializer.serialize_recent_records(game)

        assert result == ""

    def test_hand_with_no_rounds_shows_incomplete(self, default_game_metadata):
        """Incomplete hand (no outcome) shows '(incomplete)'."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Alice", Seat.SEAT_0, PositionName.BUTTON),
        }
        hand = make_hand_record(1, player_records, outcome=None)
        game = make_game_record("game1", default_game_metadata, [hand])

        result = RecordToLlmContextSerializer.serialize_recent_records(game)

        assert "(incomplete)" in result

    def test_multiple_winners_shows_comma_separated_names(self, default_game_metadata):
        """Split pot shows all winners comma-separated."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Alice", Seat.SEAT_0, PositionName.BUTTON),
            "p2": make_hand_level_player_record("p2", "Bob", Seat.SEAT_1, PositionName.SMALL_BLIND),
        }
        outcome = make_hand_outcome(
            winner_ids=("p1", "p2"),
            pot_amount=200,
            player_outcomes=(
                PlayerOutcome("p1", "Alice", ChipAmount(100), ChipAmount(1100)),
                PlayerOutcome("p2", "Bob", ChipAmount(100), ChipAmount(1100)),
            ),
        )
        hand = make_hand_record(1, player_records, outcome=outcome)
        game = make_game_record("game1", default_game_metadata, [hand])

        result = RecordToLlmContextSerializer.serialize_recent_records(game)

        assert "Winner=Alice,Bob" in result or "Winner=Bob,Alice" in result

    def test_showdown_shows_shown_hands(self, default_game_metadata):
        """Showdown includes shown hands in summary."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Alice", Seat.SEAT_0, PositionName.BUTTON),
            "p2": make_hand_level_player_record("p2", "Bob", Seat.SEAT_1, PositionName.SMALL_BLIND),
        }
        hole_cards_1 = Hand(Card(Suit.HEARTS, Rank.ACE), Card(Suit.SPADES, Rank.KING))
        hole_cards_2 = Hand(Card(Suit.DIAMONDS, Rank.QUEEN), Card(Suit.CLUBS, Rank.JACK))
        showdown_results = (
            make_showdown_result("p1", "Alice", hole_cards_1),
            make_showdown_result("p2", "Bob", hole_cards_2),
        )
        outcome = make_hand_outcome(
            winner_ids=("p1",),
            pot_amount=200,
            was_showdown=True,
            showdown_results=showdown_results,
            player_outcomes=(
                PlayerOutcome("p1", "Alice", ChipAmount(200), ChipAmount(1200)),
                PlayerOutcome("p2", "Bob", ChipAmount(0), ChipAmount(800)),
            ),
        )
        hand = make_hand_record(1, player_records, outcome=outcome)
        game = make_game_record("game1", default_game_metadata, [hand])

        result = RecordToLlmContextSerializer.serialize_recent_records(game)

        assert "showed" in result
        assert "Alice showed" in result

    def test_max_hands_limits_output(self, default_game_metadata):
        """max_hands parameter limits number of hands returned."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Alice", Seat.SEAT_0, PositionName.BUTTON),
        }
        hands = []
        for i in range(1, 6):
            outcome = make_hand_outcome(
                winner_ids=("p1",),
                pot_amount=100,
                player_outcomes=(
                    PlayerOutcome("p1", "Alice", ChipAmount(100), ChipAmount(1000 + i * 100)),
                ),
            )
            hand = make_hand_record(i, player_records, outcome=outcome)
            hands.append(hand)

        game = make_game_record("game1", default_game_metadata, hands)

        result = RecordToLlmContextSerializer.serialize_recent_records(game, max_hands=2)

        # Should only see H5 and H4 (most recent 2)
        assert "H5:" in result
        assert "H4:" in result
        assert "H3:" not in result
        assert "H2:" not in result
        assert "H1:" not in result

    def test_current_hand_actions_header_format(self, default_game_metadata):
        """Current hand actions starts with 'ACTIONS THIS HAND:'."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Alice", Seat.SEAT_0, PositionName.BUTTON),
        }
        hand = make_hand_record(1, player_records, rounds=[])

        result = RecordToLlmContextSerializer.serialize_current_hand_actions(hand, "pre_flop")

        assert result.startswith("ACTIONS THIS HAND:")

    def test_multiple_phases_serialized_in_order(self, default_game_metadata):
        """Multiple betting phases appear in correct order."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Alice", Seat.SEAT_0, PositionName.BUTTON),
            "p2": make_hand_level_player_record("p2", "Bob", Seat.SEAT_1, PositionName.BIG_BLIND),
        }
        round_records = {
            "p1": make_round_level_player_record("p1", "Alice", Seat.SEAT_0),
            "p2": make_round_level_player_record("p2", "Bob", Seat.SEAT_1),
        }
        preflop_turn = make_turn_record("p1", "Alice", Seat.SEAT_0, ActionType.RAISE, amount=60)
        preflop_round = make_round_record(GamePhase.PRE_FLOP, round_records, [preflop_turn])
        flop_turn = make_turn_record(
            "p2", "Bob", Seat.SEAT_1, ActionType.BET, amount=100, phase=GamePhase.FLOP
        )
        flop_round = make_round_record(GamePhase.FLOP, round_records, [flop_turn])
        hand = make_hand_record(1, player_records, [preflop_round, flop_round])

        result = RecordToLlmContextSerializer.serialize_current_hand_actions(hand, "turn")

        # Verify order
        preflop_pos = result.find("PRE_FLOP:")
        flop_pos = result.find("FLOP:")
        turn_pos = result.find("TURN:")
        assert preflop_pos < flop_pos < turn_pos

    def test_phase_names_are_uppercase(self, default_game_metadata):
        """Phase names in output are uppercase."""
        player_records = {
            "p1": make_hand_level_player_record("p1", "Alice", Seat.SEAT_0, PositionName.BUTTON),
        }
        hand = make_hand_record(1, player_records, rounds=[])

        result = RecordToLlmContextSerializer.serialize_current_hand_actions(hand, "pre_flop")

        assert "PRE_FLOP:" in result
        assert "pre_flop:" not in result


class TestSerializeRecentRecordsIntegration:
    """Integration tests for serialize_recent_records with complex multi-hand games."""

    def test_three_hand_game_with_showdown_and_fold_wins(self, default_game_metadata):
        """
        Three-hand game with proper button rotation: fold win, showdown, and all-in.

        Scenario (button rotates each hand):
        - Hand 1: Alice(BTN), Bob(SB), Carol(BB) - Alice raises, both fold -> Alice wins
        - Hand 2: Bob(BTN), Carol(SB), Alice(BB) - Bob raises, Carol calls, flop action, Carol wins showdown
        - Hand 3: Carol(BTN), Alice(SB), Bob(BB) - Carol raises, Alice all-in, Bob folds, Carol calls, Alice wins

        Expected output shows most recent hands first (H3, H2, H1).
        """
        # === EXPECTED OUTPUT ===
        expected_lines = [
            "=== PREVIOUS HANDS ===",
            # Hand 3 (Carol=BTN, Alice=SB all-in wins)
            "H3: Winner=Alice, Pot=650, Showdown=yes, Alice showed A♠️ K❤️; Carol showed Q♦️ J♣️",
            "Stacks: Carol(BTN)=1150, Alice(SB)=800, Bob(BB)=900",
            "PRE_FLOP: Carol(BTN):R100, Alice(SB):AI400, Bob(BB):F, Carol(BTN):C",
            # Hand 2 (Bob=BTN, Carol wins showdown)
            "H2: Winner=Carol, Pot=300, Showdown=yes, Carol showed A♠️ K❤️; Bob showed Q♦️ J♣️",
            "Stacks: Bob(BTN)=975, Carol(SB)=950, Alice(BB)=1075",
            "PRE_FLOP: Bob(BTN):R100, Carol(SB):C, Alice(BB):F",
            "FLOP: Carol(SB):X, Bob(BTN):B50, Carol(SB):C",
            # Hand 1 (Alice=BTN, fold win)
            "H1: Winner=Alice, Pot=75, Showdown=no",
            "Stacks: Alice(BTN)=1000, Bob(SB)=1000, Carol(BB)=1000",
            "PRE_FLOP: Alice(BTN):R60, Bob(SB):F, Carol(BB):F",
        ]

        # === BUILD INPUT DATA ===
        # Hand 1: Alice(BTN), Bob(SB), Carol(BB)
        # Alice raises to 60, Bob and Carol fold
        # Pot = 25 + 50 = 75 (blinds that Alice wins)
        hand1_player_records = {
            "alice": make_hand_level_player_record(
                "alice", "Alice", Seat.SEAT_0, PositionName.BUTTON, starting_chips=1000
            ),
            "bob": make_hand_level_player_record(
                "bob", "Bob", Seat.SEAT_1, PositionName.SMALL_BLIND, starting_chips=1000
            ),
            "carol": make_hand_level_player_record(
                "carol", "Carol", Seat.SEAT_2, PositionName.BIG_BLIND, starting_chips=1000
            ),
        }
        hand1_round_records = {
            "alice": make_round_level_player_record("alice", "Alice", Seat.SEAT_0),
            "bob": make_round_level_player_record("bob", "Bob", Seat.SEAT_1),
            "carol": make_round_level_player_record("carol", "Carol", Seat.SEAT_2),
        }
        hand1_preflop = make_round_record(
            GamePhase.PRE_FLOP,
            hand1_round_records,
            [
                make_turn_record(
                    "alice", "Alice", Seat.SEAT_0, ActionType.RAISE, 60, turn_number=1
                ),
                make_turn_record("bob", "Bob", Seat.SEAT_1, ActionType.FOLD, turn_number=2),
                make_turn_record("carol", "Carol", Seat.SEAT_2, ActionType.FOLD, turn_number=3),
            ],
        )
        hand1_outcome = make_hand_outcome(
            winner_ids=("alice",),
            pot_amount=75,  # 25 + 50 blinds
            was_showdown=False,
            player_outcomes=(
                PlayerOutcome("alice", "Alice", ChipAmount(75), ChipAmount(1075)),
                PlayerOutcome("bob", "Bob", ChipAmount(0), ChipAmount(975)),
                PlayerOutcome("carol", "Carol", ChipAmount(0), ChipAmount(950)),
            ),
        )
        hand1 = make_hand_record(1, hand1_player_records, [hand1_preflop], hand1_outcome)

        # Hand 2: Bob(BTN), Carol(SB), Alice(BB) - button rotated
        # Bob raises to 100, Carol calls, Alice folds
        # Flop: Carol checks, Bob bets 50, Carol calls
        # Carol wins showdown
        hand2_player_records = {
            "bob": make_hand_level_player_record(
                "bob", "Bob", Seat.SEAT_1, PositionName.BUTTON, starting_chips=975
            ),
            "carol": make_hand_level_player_record(
                "carol", "Carol", Seat.SEAT_2, PositionName.SMALL_BLIND, starting_chips=950
            ),
            "alice": make_hand_level_player_record(
                "alice", "Alice", Seat.SEAT_0, PositionName.BIG_BLIND, starting_chips=1075
            ),
        }
        hand2_round_records = {
            "bob": make_round_level_player_record("bob", "Bob", Seat.SEAT_1),
            "carol": make_round_level_player_record("carol", "Carol", Seat.SEAT_2),
            "alice": make_round_level_player_record("alice", "Alice", Seat.SEAT_0),
        }
        hand2_preflop = make_round_record(
            GamePhase.PRE_FLOP,
            hand2_round_records,
            [
                make_turn_record("bob", "Bob", Seat.SEAT_1, ActionType.RAISE, 100, turn_number=1),
                make_turn_record("carol", "Carol", Seat.SEAT_2, ActionType.CALL, turn_number=2),
                make_turn_record("alice", "Alice", Seat.SEAT_0, ActionType.FOLD, turn_number=3),
            ],
        )
        hand2_flop = make_round_record(
            GamePhase.FLOP,
            hand2_round_records,
            [
                make_turn_record(
                    "carol",
                    "Carol",
                    Seat.SEAT_2,
                    ActionType.CHECK,
                    phase=GamePhase.FLOP,
                    turn_number=1,
                ),
                make_turn_record(
                    "bob",
                    "Bob",
                    Seat.SEAT_1,
                    ActionType.BET,
                    50,
                    phase=GamePhase.FLOP,
                    turn_number=2,
                ),
                make_turn_record(
                    "carol",
                    "Carol",
                    Seat.SEAT_2,
                    ActionType.CALL,
                    phase=GamePhase.FLOP,
                    turn_number=3,
                ),
            ],
        )
        carol_cards = Hand(Card(Suit.SPADES, Rank.ACE), Card(Suit.HEARTS, Rank.KING))
        bob_cards = Hand(Card(Suit.DIAMONDS, Rank.QUEEN), Card(Suit.CLUBS, Rank.JACK))
        hand2_showdown = (
            make_showdown_result("carol", "Carol", carol_cards),
            make_showdown_result("bob", "Bob", bob_cards),
        )
        hand2_outcome = make_hand_outcome(
            winner_ids=("carol",),
            pot_amount=300,  # 100+100 preflop + 50+50 flop = 300
            was_showdown=True,
            showdown_results=hand2_showdown,
            player_outcomes=(
                PlayerOutcome("bob", "Bob", ChipAmount(0), ChipAmount(825)),
                PlayerOutcome("carol", "Carol", ChipAmount(300), ChipAmount(1150)),
                PlayerOutcome("alice", "Alice", ChipAmount(0), ChipAmount(1025)),
            ),
        )
        hand2 = make_hand_record(
            2, hand2_player_records, [hand2_preflop, hand2_flop], hand2_outcome
        )

        # Hand 3: Carol(BTN), Alice(SB), Bob(BB) - button rotated again
        # Carol raises to 100, Alice goes all-in for 400, Bob folds, Carol calls
        # Alice wins at showdown
        hand3_player_records = {
            "carol": make_hand_level_player_record(
                "carol", "Carol", Seat.SEAT_2, PositionName.BUTTON, starting_chips=1150
            ),
            "alice": make_hand_level_player_record(
                "alice", "Alice", Seat.SEAT_0, PositionName.SMALL_BLIND, starting_chips=800
            ),
            "bob": make_hand_level_player_record(
                "bob", "Bob", Seat.SEAT_1, PositionName.BIG_BLIND, starting_chips=900
            ),
        }
        hand3_round_records = {
            "carol": make_round_level_player_record("carol", "Carol", Seat.SEAT_2),
            "alice": make_round_level_player_record("alice", "Alice", Seat.SEAT_0),
            "bob": make_round_level_player_record("bob", "Bob", Seat.SEAT_1),
        }
        hand3_preflop = make_round_record(
            GamePhase.PRE_FLOP,
            hand3_round_records,
            [
                make_turn_record(
                    "carol", "Carol", Seat.SEAT_2, ActionType.RAISE, 100, turn_number=1
                ),
                make_turn_record(
                    "alice", "Alice", Seat.SEAT_0, ActionType.ALL_IN, 400, turn_number=2
                ),
                make_turn_record("bob", "Bob", Seat.SEAT_1, ActionType.FOLD, turn_number=3),
                make_turn_record("carol", "Carol", Seat.SEAT_2, ActionType.CALL, turn_number=4),
            ],
        )
        alice_win_cards = Hand(Card(Suit.SPADES, Rank.ACE), Card(Suit.HEARTS, Rank.KING))
        carol_lose_cards = Hand(Card(Suit.DIAMONDS, Rank.QUEEN), Card(Suit.CLUBS, Rank.JACK))
        hand3_showdown = (
            make_showdown_result("alice", "Alice", alice_win_cards),
            make_showdown_result("carol", "Carol", carol_lose_cards),
        )
        hand3_outcome = make_hand_outcome(
            winner_ids=("alice",),
            pot_amount=650,  # Both put in ~400 + Bob's BB 50 = ~650 (simplified)
            was_showdown=True,
            showdown_results=hand3_showdown,
            player_outcomes=(
                PlayerOutcome("alice", "Alice", ChipAmount(650), ChipAmount(1050)),
                PlayerOutcome("carol", "Carol", ChipAmount(0), ChipAmount(750)),
                PlayerOutcome("bob", "Bob", ChipAmount(0), ChipAmount(850)),
            ),
        )
        hand3 = make_hand_record(3, hand3_player_records, [hand3_preflop], hand3_outcome)

        game = make_game_record("game1", default_game_metadata, [hand1, hand2, hand3])

        # === ACT ===
        actual = RecordToLlmContextSerializer.serialize_recent_records(game)

        # === ASSERT ===
        for expected_line in expected_lines:
            assert (
                expected_line in actual
            ), f"Missing expected line: {expected_line}\n\nActual output:\n{actual}"

    def test_two_hand_game_from_viewer_perspective_with_split_pot(self, default_game_metadata):
        """
        Two-hand game from viewer (Bob) perspective with split pot.

        Scenario:
        - Hand 1: Alice(BTN) raises, Bob(SB) 3-bets, everyone folds -> Bob wins without showdown
        - Hand 2: Button rotates. Bob(BTN) raises, Carol(SB) folds, Alice(BB) calls,
                  goes to river, split pot at showdown

        Expected: Viewer appears as 'you' everywhere, button rotates between hands.
        """
        # === EXPECTED OUTPUT ===
        expected_lines = [
            "=== PREVIOUS HANDS ===",
            # Hand 2 (split pot with viewer as BTN)
            "H2: Winner=you,Alice, Pot=400, Showdown=yes",
            "you showed A♠️ K❤️",
            "Stacks: you(BTN)=1110, Carol(SB)=950, Alice(BB)=940",
            "PRE_FLOP: you(BTN):R100, Carol(SB):F, Alice(BB):C",
            "FLOP: Alice(BB):X, you(BTN):B100, Alice(BB):C",
            # Hand 1 (viewer wins as SB)
            "H1: Winner=you, Pot=135, Showdown=no",
            "Stacks: Alice(BTN)=1000, you(SB)=1000, Carol(BB)=1000",
            "PRE_FLOP: Alice(BTN):R60, you(SB):R150, Carol(BB):F, Alice(BTN):F",
        ]

        # === BUILD INPUT DATA ===
        # Hand 1: Alice(BTN), Bob(SB), Carol(BB)
        # Alice raises to 60, Bob 3-bets to 150, Carol folds, Alice folds
        # Pot = 25(SB posted) + 50(BB posted) + 60(Alice's raise) = 135 when Alice folds
        hand1_player_records = {
            "alice": make_hand_level_player_record(
                "alice", "Alice", Seat.SEAT_0, PositionName.BUTTON, starting_chips=1000
            ),
            "bob": make_hand_level_player_record(
                "bob", "Bob", Seat.SEAT_1, PositionName.SMALL_BLIND, starting_chips=1000
            ),
            "carol": make_hand_level_player_record(
                "carol", "Carol", Seat.SEAT_2, PositionName.BIG_BLIND, starting_chips=1000
            ),
        }
        hand1_round_records = {
            "alice": make_round_level_player_record("alice", "Alice", Seat.SEAT_0),
            "bob": make_round_level_player_record("bob", "Bob", Seat.SEAT_1),
            "carol": make_round_level_player_record("carol", "Carol", Seat.SEAT_2),
        }
        hand1_preflop = make_round_record(
            GamePhase.PRE_FLOP,
            hand1_round_records,
            [
                make_turn_record(
                    "alice", "Alice", Seat.SEAT_0, ActionType.RAISE, 60, turn_number=1
                ),
                make_turn_record("bob", "Bob", Seat.SEAT_1, ActionType.RAISE, 150, turn_number=2),
                make_turn_record("carol", "Carol", Seat.SEAT_2, ActionType.FOLD, turn_number=3),
                make_turn_record("alice", "Alice", Seat.SEAT_0, ActionType.FOLD, turn_number=4),
            ],
        )
        hand1_outcome = make_hand_outcome(
            winner_ids=("bob",),
            pot_amount=135,  # 25 + 50 + 60 = 135
            was_showdown=False,
            player_outcomes=(
                PlayerOutcome("alice", "Alice", ChipAmount(0), ChipAmount(940)),
                PlayerOutcome("bob", "Bob", ChipAmount(135), ChipAmount(1110)),
                PlayerOutcome("carol", "Carol", ChipAmount(0), ChipAmount(950)),
            ),
        )
        hand1 = make_hand_record(1, hand1_player_records, [hand1_preflop], hand1_outcome)

        # Hand 2: Button rotates -> Bob(BTN), Carol(SB), Alice(BB)
        # Bob raises to 100, Carol folds, Alice calls
        # Flop: Alice checks, Bob bets 100, Alice calls
        # Goes to showdown with split pot (both have AK)
        hand2_player_records = {
            "bob": make_hand_level_player_record(
                "bob", "Bob", Seat.SEAT_1, PositionName.BUTTON, starting_chips=1110
            ),
            "carol": make_hand_level_player_record(
                "carol", "Carol", Seat.SEAT_2, PositionName.SMALL_BLIND, starting_chips=950
            ),
            "alice": make_hand_level_player_record(
                "alice", "Alice", Seat.SEAT_0, PositionName.BIG_BLIND, starting_chips=940
            ),
        }
        hand2_round_records = {
            "bob": make_round_level_player_record("bob", "Bob", Seat.SEAT_1),
            "carol": make_round_level_player_record("carol", "Carol", Seat.SEAT_2),
            "alice": make_round_level_player_record("alice", "Alice", Seat.SEAT_0),
        }
        hand2_preflop = make_round_record(
            GamePhase.PRE_FLOP,
            hand2_round_records,
            [
                make_turn_record("bob", "Bob", Seat.SEAT_1, ActionType.RAISE, 100, turn_number=1),
                make_turn_record("carol", "Carol", Seat.SEAT_2, ActionType.FOLD, turn_number=2),
                make_turn_record("alice", "Alice", Seat.SEAT_0, ActionType.CALL, turn_number=3),
            ],
        )
        hand2_flop = make_round_record(
            GamePhase.FLOP,
            hand2_round_records,
            [
                make_turn_record(
                    "alice",
                    "Alice",
                    Seat.SEAT_0,
                    ActionType.CHECK,
                    phase=GamePhase.FLOP,
                    turn_number=1,
                ),
                make_turn_record(
                    "bob",
                    "Bob",
                    Seat.SEAT_1,
                    ActionType.BET,
                    100,
                    phase=GamePhase.FLOP,
                    turn_number=2,
                ),
                make_turn_record(
                    "alice",
                    "Alice",
                    Seat.SEAT_0,
                    ActionType.CALL,
                    phase=GamePhase.FLOP,
                    turn_number=3,
                ),
            ],
        )
        bob_cards = Hand(Card(Suit.SPADES, Rank.ACE), Card(Suit.HEARTS, Rank.KING))
        alice_cards = Hand(Card(Suit.HEARTS, Rank.ACE), Card(Suit.DIAMONDS, Rank.KING))
        hand2_showdown = (
            make_showdown_result("bob", "Bob", bob_cards),
            make_showdown_result("alice", "Alice", alice_cards),
        )
        hand2_outcome = make_hand_outcome(
            winner_ids=("bob", "alice"),  # Split pot
            pot_amount=400,  # 25 + 50 + 100 + 100 (pre) + 100 + 100 (flop) = ~400
            was_showdown=True,
            showdown_results=hand2_showdown,
            player_outcomes=(
                PlayerOutcome("bob", "Bob", ChipAmount(200), ChipAmount(1110)),
                PlayerOutcome("alice", "Alice", ChipAmount(200), ChipAmount(940)),
                PlayerOutcome("carol", "Carol", ChipAmount(0), ChipAmount(925)),
            ),
        )
        hand2 = make_hand_record(
            2, hand2_player_records, [hand2_preflop, hand2_flop], hand2_outcome
        )

        game = make_game_record("game1", default_game_metadata, [hand1, hand2])

        # === ACT ===
        actual = RecordToLlmContextSerializer.serialize_recent_records(game, viewer_id="bob")

        # === ASSERT ===
        for expected_line in expected_lines:
            assert (
                expected_line in actual
            ), f"Missing expected line: {expected_line}\n\nActual output:\n{actual}"

        # Verify Bob never appears as "Bob" - always as "you"
        assert (
            "Bob(" not in actual
        ), f"Bob should appear as 'you', not 'Bob'\n\nActual output:\n{actual}"


class TestSerializeCurrentHandActionsIntegration:
    """Integration tests for serialize_current_hand_actions with complex multi-phase hands."""

    def test_hand_on_turn_with_preflop_and_flop_actions(self, default_game_metadata):
        """
        Complex hand in progress on the turn.

        Scenario:
        - Pre-flop: UTG raises, CO calls, BTN 3-bets, SB folds, BB calls, UTG folds, CO calls
        - Flop: BB checks, CO bets, BTN raises, BB folds, CO calls
        - Turn: Decision point (current phase)

        Expected output shows all previous action and '?' for current phase.
        """
        # === EXPECTED OUTPUT ===
        expected_output = """ACTIONS THIS HAND:
  PRE_FLOP: Dave(UTG):R60, Eve(CO):C, Alice(BTN):R180, Bob(SB):F, Carol(BB):C, Dave(UTG):F, Eve(CO):C
  FLOP: Carol(BB):X, Eve(CO):B100, Alice(BTN):R250, Carol(BB):F, Eve(CO):C
  TURN: ?"""

        # === BUILD INPUT DATA ===
        player_records = {
            "alice": make_hand_level_player_record(
                "alice", "Alice", Seat.SEAT_0, PositionName.BUTTON, starting_chips=2000
            ),
            "bob": make_hand_level_player_record(
                "bob", "Bob", Seat.SEAT_1, PositionName.SMALL_BLIND, starting_chips=1500
            ),
            "carol": make_hand_level_player_record(
                "carol", "Carol", Seat.SEAT_2, PositionName.BIG_BLIND, starting_chips=1800
            ),
            "dave": make_hand_level_player_record(
                "dave", "Dave", Seat.SEAT_3, PositionName.UNDER_THE_GUN, starting_chips=1200
            ),
            "eve": make_hand_level_player_record(
                "eve", "Eve", Seat.SEAT_4, PositionName.CUTOFF, starting_chips=2200
            ),
        }
        round_records = {
            "alice": make_round_level_player_record("alice", "Alice", Seat.SEAT_0),
            "bob": make_round_level_player_record("bob", "Bob", Seat.SEAT_1),
            "carol": make_round_level_player_record("carol", "Carol", Seat.SEAT_2),
            "dave": make_round_level_player_record("dave", "Dave", Seat.SEAT_3),
            "eve": make_round_level_player_record("eve", "Eve", Seat.SEAT_4),
        }

        # Pre-flop: UTG raises, CO calls, BTN 3-bets, SB folds, BB calls, UTG folds, CO calls
        preflop_round = make_round_record(
            GamePhase.PRE_FLOP,
            round_records,
            [
                make_turn_record("dave", "Dave", Seat.SEAT_3, ActionType.RAISE, 60, turn_number=1),
                make_turn_record("eve", "Eve", Seat.SEAT_4, ActionType.CALL, turn_number=2),
                make_turn_record(
                    "alice", "Alice", Seat.SEAT_0, ActionType.RAISE, 180, turn_number=3
                ),
                make_turn_record("bob", "Bob", Seat.SEAT_1, ActionType.FOLD, turn_number=4),
                make_turn_record("carol", "Carol", Seat.SEAT_2, ActionType.CALL, turn_number=5),
                make_turn_record("dave", "Dave", Seat.SEAT_3, ActionType.FOLD, turn_number=6),
                make_turn_record("eve", "Eve", Seat.SEAT_4, ActionType.CALL, turn_number=7),
            ],
        )

        # Flop: BB checks, CO bets, BTN raises, BB folds, CO calls
        flop_round = make_round_record(
            GamePhase.FLOP,
            round_records,
            [
                make_turn_record(
                    "carol",
                    "Carol",
                    Seat.SEAT_2,
                    ActionType.CHECK,
                    phase=GamePhase.FLOP,
                    turn_number=1,
                ),
                make_turn_record(
                    "eve",
                    "Eve",
                    Seat.SEAT_4,
                    ActionType.BET,
                    100,
                    phase=GamePhase.FLOP,
                    turn_number=2,
                ),
                make_turn_record(
                    "alice",
                    "Alice",
                    Seat.SEAT_0,
                    ActionType.RAISE,
                    250,
                    phase=GamePhase.FLOP,
                    turn_number=3,
                ),
                make_turn_record(
                    "carol",
                    "Carol",
                    Seat.SEAT_2,
                    ActionType.FOLD,
                    phase=GamePhase.FLOP,
                    turn_number=4,
                ),
                make_turn_record(
                    "eve", "Eve", Seat.SEAT_4, ActionType.CALL, phase=GamePhase.FLOP, turn_number=5
                ),
            ],
        )

        hand = make_hand_record(1, player_records, [preflop_round, flop_round])

        # === ACT ===
        actual = RecordToLlmContextSerializer.serialize_current_hand_actions(hand, "turn")

        # === ASSERT ===
        assert (
            actual.strip() == expected_output.strip()
        ), f"Output mismatch.\n\nExpected:\n{expected_output}\n\nActual:\n{actual}"

    def test_hand_on_river_with_all_phases_and_all_in(self, default_game_metadata):
        """
        Hand deep in the river with action across all phases including all-in.

        Scenario:
        - Pre-flop: SB raises, BB calls
        - Flop: SB bets, BB raises, SB calls
        - Turn: SB checks, BB bets, SB all-in, BB calls
        - River: Decision point with some action already

        Tests all action types across multiple phases.
        """
        # === EXPECTED OUTPUT ===
        expected_output = """ACTIONS THIS HAND:
  PRE_FLOP: Alice(SB):R100, Bob(BB):C
  FLOP: Alice(SB):B150, Bob(BB):R400, Alice(SB):C
  TURN: Alice(SB):X, Bob(BB):B300, Alice(SB):AI800, Bob(BB):C
  RIVER: Bob(BB):X, ?"""

        # === BUILD INPUT DATA ===
        player_records = {
            "alice": make_hand_level_player_record(
                "alice", "Alice", Seat.SEAT_0, PositionName.SMALL_BLIND, starting_chips=1500
            ),
            "bob": make_hand_level_player_record(
                "bob", "Bob", Seat.SEAT_1, PositionName.BIG_BLIND, starting_chips=2000
            ),
        }
        round_records = {
            "alice": make_round_level_player_record("alice", "Alice", Seat.SEAT_0),
            "bob": make_round_level_player_record("bob", "Bob", Seat.SEAT_1),
        }

        # Pre-flop
        preflop_round = make_round_record(
            GamePhase.PRE_FLOP,
            round_records,
            [
                make_turn_record(
                    "alice", "Alice", Seat.SEAT_0, ActionType.RAISE, 100, turn_number=1
                ),
                make_turn_record("bob", "Bob", Seat.SEAT_1, ActionType.CALL, turn_number=2),
            ],
        )

        # Flop
        flop_round = make_round_record(
            GamePhase.FLOP,
            round_records,
            [
                make_turn_record(
                    "alice",
                    "Alice",
                    Seat.SEAT_0,
                    ActionType.BET,
                    150,
                    phase=GamePhase.FLOP,
                    turn_number=1,
                ),
                make_turn_record(
                    "bob",
                    "Bob",
                    Seat.SEAT_1,
                    ActionType.RAISE,
                    400,
                    phase=GamePhase.FLOP,
                    turn_number=2,
                ),
                make_turn_record(
                    "alice",
                    "Alice",
                    Seat.SEAT_0,
                    ActionType.CALL,
                    phase=GamePhase.FLOP,
                    turn_number=3,
                ),
            ],
        )

        # Turn
        turn_round = make_round_record(
            GamePhase.TURN,
            round_records,
            [
                make_turn_record(
                    "alice",
                    "Alice",
                    Seat.SEAT_0,
                    ActionType.CHECK,
                    phase=GamePhase.TURN,
                    turn_number=1,
                ),
                make_turn_record(
                    "bob",
                    "Bob",
                    Seat.SEAT_1,
                    ActionType.BET,
                    300,
                    phase=GamePhase.TURN,
                    turn_number=2,
                ),
                make_turn_record(
                    "alice",
                    "Alice",
                    Seat.SEAT_0,
                    ActionType.ALL_IN,
                    800,
                    phase=GamePhase.TURN,
                    turn_number=3,
                ),
                make_turn_record(
                    "bob", "Bob", Seat.SEAT_1, ActionType.CALL, phase=GamePhase.TURN, turn_number=4
                ),
            ],
        )

        # River (current phase with one action)
        river_round = make_round_record(
            GamePhase.RIVER,
            round_records,
            [
                make_turn_record(
                    "bob",
                    "Bob",
                    Seat.SEAT_1,
                    ActionType.CHECK,
                    phase=GamePhase.RIVER,
                    turn_number=1,
                ),
            ],
        )

        hand = make_hand_record(
            1, player_records, [preflop_round, flop_round, turn_round, river_round]
        )

        # === ACT ===
        actual = RecordToLlmContextSerializer.serialize_current_hand_actions(hand, "river")

        # === ASSERT ===
        assert (
            actual.strip() == expected_output.strip()
        ), f"Output mismatch.\n\nExpected:\n{expected_output}\n\nActual:\n{actual}"
