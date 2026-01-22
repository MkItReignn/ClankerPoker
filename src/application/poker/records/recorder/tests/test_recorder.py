"""Behavioral tests for Recorder.

Tests focus on documenting and verifying the recorder's behavior at each
level of the game hierarchy: Game -> Hand -> Round -> Turn.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import pytest

from src.application.poker.records.models import GameMetadata
from src.application.poker.records.recorder import Recorder
from src.application.protocols.player import ActionResponse
from src.config.poker.config import PokerPlayerConfig
from src.domain.models.actions import Action, ActionType
from src.domain.models.card import Rank
from src.domain.models.chips import ChipAmount
from src.domain.models.game import Game, GamePhase, HandOutcome
from src.domain.models.player import (BettingRoundActionStatus,
                                      HandParticipationStatus, Player)
from src.domain.models.seat import Seat

from .conftest import BIG_BLIND, SMALL_BLIND, STARTING_CHIPS, make_hole_cards


class TestGameLifecycle:
    """Tests for game-level recording (record_game_start, record_game_complete)."""

    def test_registers_all_players_with_initial_state(
        self,
        recorder: Recorder,
        two_player_game: Game,
        game_metadata: GameMetadata,
    ) -> None:
        """All players are registered with correct initial chips and seat."""
        recorder.record_game_start(two_player_game, game_metadata)

        assert recorder.record is not None
        assert len(recorder.record.player_records) == 2

        p1_state = recorder.record.player_records["player-1"]
        assert p1_state.player_name == "Alice"
        assert p1_state.chips == STARTING_CHIPS
        assert p1_state.seat == Seat.SEAT_0
        assert p1_state.hands_played == 0
        assert p1_state.is_eliminated is False

        p2_state = recorder.record.player_records["player-2"]
        assert p2_state.player_name == "Bob"
        assert p2_state.chips == STARTING_CHIPS
        assert p2_state.seat == Seat.SEAT_1

    def test_stores_game_id_from_state(
        self,
        recorder: Recorder,
        two_player_game: Game,
        game_metadata: GameMetadata,
    ) -> None:
        """Game ID is captured from the game state."""
        recorder.record_game_start(two_player_game, game_metadata)

        assert recorder.record is not None
        assert recorder.record.game_id == two_player_game.id

    def test_stores_tournament_metadata(
        self,
        recorder: Recorder,
        two_player_game: Game,
        game_metadata: GameMetadata,
    ) -> None:
        """Tournament configuration metadata is captured."""
        recorder.record_game_start(two_player_game, game_metadata)

        assert recorder.record is not None
        assert recorder.record.metadata.seed == game_metadata.seed
        assert recorder.record.metadata.buy_in_amount == game_metadata.buy_in_amount
        assert recorder.record.metadata.starting_chip_stack == game_metadata.starting_chip_stack

    def test_record_game_complete_sets_completion_timestamp(
        self,
        recorder: Recorder,
        two_player_game: Game,
        game_metadata: GameMetadata,
    ) -> None:
        """Completing the game sets the completion timestamp in metadata."""
        recorder.record_game_start(two_player_game, game_metadata)
        completed_at = datetime.now()

        recorder.record_game_complete(completed_at)

        assert recorder.record is not None
        assert recorder.record.metadata.completed_at == completed_at

    def test_raises_on_unknown_player_id(
        self,
        two_player_game: Game,
        game_metadata: GameMetadata,
    ) -> None:
        """Raises KeyError when a player ID is not in the player_configs mapping."""
        from src.domain.models.llm_model import LlmModel

        incomplete_configs = {
            "player-1": PokerPlayerConfig(
                player_id="player-1",
                name="Alice",
                model_id=LlmModel.OPENAI_GPT4O_MINI,
            )
        }  # Missing player-2
        recorder = Recorder(player_configs=incomplete_configs)

        with pytest.raises(KeyError, match="player-2"):
            recorder.record_game_start(two_player_game, game_metadata)


class TestHandLifecycle:
    """Tests for hand-level recording (record_hand_start, record_hand_complete)."""

    def test_captures_player_positions(
        self,
        recorder: Recorder,
        three_player_game: Game,
        game_metadata: GameMetadata,
    ) -> None:
        """Each player's position (BTN, SB, BB) is recorded at hand start."""
        recorder.record_game_start(three_player_game, game_metadata)
        recorder.record_hand_start(three_player_game)

        assert recorder.record is not None
        assert recorder.record.current_hand is not None

        hand = recorder.record.current_hand
        positions_recorded = {pid: state.position for pid, state in hand.player_records.items()}

        # At least one position should be assigned
        assert any(pos is not None for pos in positions_recorded.values())

    def test_captures_hole_cards(
        self,
        recorder: Recorder,
        two_player_game: Game,
        game_metadata: GameMetadata,
    ) -> None:
        """Hole cards are captured for each player at hand start."""
        recorder.record_game_start(two_player_game, game_metadata)
        recorder.record_hand_start(two_player_game)

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None

        p1_state = hand.player_records["player-1"]
        assert p1_state.hole_cards is not None
        assert p1_state.hole_cards.card1.rank == Rank.ACE

    def test_captures_button_seat_and_blinds(
        self,
        recorder: Recorder,
        two_player_game: Game,
        game_metadata: GameMetadata,
    ) -> None:
        """Button seat and blind levels are recorded at hand start."""
        recorder.record_game_start(two_player_game, game_metadata)
        recorder.record_hand_start(two_player_game)

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None
        assert hand.button_seat == two_player_game.button_seat
        assert hand.blinds == two_player_game.current_blind_level

    def test_captures_hand_number(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        game_metadata: GameMetadata,
    ) -> None:
        """Hand number is captured correctly."""
        players = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                stack_at_hand_start=STARTING_CHIPS,
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                stack_at_hand_start=STARTING_CHIPS,
            ),
        ]
        game = game_factory(players=players, hand_number=5)

        recorder.record_game_start(game, game_metadata)
        recorder.record_hand_start(game)

        assert recorder.record is not None
        assert recorder.record.current_hand is not None
        assert recorder.record.current_hand.hand_number == 5

    def test_excludes_eliminated_players(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        game_metadata: GameMetadata,
    ) -> None:
        """Eliminated players are not included in hand-level player states."""
        players = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                stack_at_hand_start=STARTING_CHIPS,
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                participation_status=HandParticipationStatus.ELIMINATED,
                remaining_chips=ChipAmount(0),
                stack_at_hand_start=ChipAmount(0),
            ),
            player_factory(
                player_id="player-3",
                seat=Seat.SEAT_2,
                stack_at_hand_start=STARTING_CHIPS,
            ),
        ]
        game = game_factory(players=players)

        recorder.record_game_start(game, game_metadata)
        recorder.record_hand_start(game)

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None

        # Only non-eliminated players should be in hand states
        assert "player-1" in hand.player_records
        assert "player-2" not in hand.player_records
        assert "player-3" in hand.player_records

    def test_starting_chips_captured_correctly(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        game_metadata: GameMetadata,
    ) -> None:
        """Starting chips at hand start equals remaining chips."""
        current_chips = ChipAmount(800)
        players = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                remaining_chips=current_chips,
                stack_at_hand_start=current_chips,
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                remaining_chips=STARTING_CHIPS,
                stack_at_hand_start=STARTING_CHIPS,
            ),
        ]
        game = game_factory(players=players)

        recorder.record_game_start(game, game_metadata)
        recorder.record_hand_start(game)

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None

        p1_state = hand.player_records["player-1"]
        assert p1_state.starting_chips == current_chips
        assert p1_state.chips == current_chips


class TestHandOutcome:
    """Tests for hand completion and outcome recording."""

    def test_records_winner_on_fold_out(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        game_metadata: GameMetadata,
    ) -> None:
        """When all but one player folds, the remaining player wins."""
        pot_amount = ChipAmount(100)
        players = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1100),  # Won the pot
                stack_at_hand_start=STARTING_CHIPS,
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(900),
                participation_status=HandParticipationStatus.FOLDED,
                stack_at_hand_start=STARTING_CHIPS,
            ),
        ]
        game = game_factory(
            players=players,
            pot_amount=pot_amount,
            outcome=HandOutcome(
                hand_number=1,
                winners=[("player-1", pot_amount)],
            ),
            current_phase=GamePhase.PRE_FLOP,
        )

        recorder.record_game_start(game, game_metadata)
        recorder.record_hand_start(game)
        recorder.record_hand_complete(game)

        assert recorder.record is not None
        assert len(recorder.record.completed_hands) == 1

        completed_hand = recorder.record.completed_hands[0]
        assert completed_hand.outcome is not None
        assert "player-1" in completed_hand.outcome.winner_ids
        assert completed_hand.outcome.was_showdown is False

    def test_records_showdown_with_hand_evaluations(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        game_metadata: GameMetadata,
    ) -> None:
        """Showdown records each player's hand evaluation."""
        pot_amount = ChipAmount(200)
        players = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1100),
                hole_cards=make_hole_cards(Rank.ACE, Rank.ACE),
                stack_at_hand_start=STARTING_CHIPS,
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(900),
                hole_cards=make_hole_cards(Rank.KING, Rank.KING),
                stack_at_hand_start=STARTING_CHIPS,
            ),
        ]
        game = game_factory(
            players=players,
            pot_amount=pot_amount,
            current_phase=GamePhase.SHOWDOWN,
            outcome=HandOutcome(
                hand_number=1,
                winners=[("player-1", pot_amount)],
            ),
        )

        recorder.record_game_start(game, game_metadata)
        recorder.record_hand_start(game)
        recorder.record_hand_complete(game)

        assert recorder.record is not None
        completed_hand = recorder.record.completed_hands[0]
        assert completed_hand.outcome is not None
        assert completed_hand.outcome.was_showdown is True
        assert len(completed_hand.outcome.showdown_results) == 2

        # Verify showdown results contain hand evaluations
        for result in completed_hand.outcome.showdown_results:
            assert result.hole_cards is not None
            assert result.hand_evaluation is not None

    def test_updates_game_level_player_state_after_hand(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        game_metadata: GameMetadata,
    ) -> None:
        """Game-level player state is updated with hand results."""
        pot_amount = ChipAmount(100)
        final_chips = ChipAmount(1100)
        players = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                remaining_chips=final_chips,
                stack_at_hand_start=STARTING_CHIPS,
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(900),
                participation_status=HandParticipationStatus.FOLDED,
                stack_at_hand_start=STARTING_CHIPS,
            ),
        ]
        game = game_factory(
            players=players,
            pot_amount=pot_amount,
            outcome=HandOutcome(
                hand_number=1,
                winners=[("player-1", pot_amount)],
            ),
        )

        recorder.record_game_start(game, game_metadata)
        recorder.record_hand_start(game)
        recorder.record_hand_complete(game)

        assert recorder.record is not None
        # Game-level state should reflect final chips and hands played
        p1_game_state = recorder.record.player_records["player-1"]
        assert p1_game_state.chips == final_chips
        assert p1_game_state.hands_played == 1


class TestRoundLifecycle:
    """Tests for round-level recording (record_round_start, record_round_complete)."""

    def test_captures_community_cards(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        game_metadata: GameMetadata,
    ) -> None:
        """Community cards are captured at round start."""
        players = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                stack_at_hand_start=STARTING_CHIPS,
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                stack_at_hand_start=STARTING_CHIPS,
            ),
        ]
        game = game_factory(
            players=players,
            current_phase=GamePhase.FLOP,
        )

        recorder.record_game_start(game, game_metadata)
        recorder.record_hand_start(game)
        recorder.record_round_start(game)

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None
        assert len(hand.rounds) == 1

        round_record = hand.rounds[0]
        assert round_record.phase == GamePhase.FLOP

    def test_tracks_player_participation_status(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        game_metadata: GameMetadata,
    ) -> None:
        """Player participation status (folded, in_hand) is captured."""
        players = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                participation_status=HandParticipationStatus.IN_HAND,
                stack_at_hand_start=STARTING_CHIPS,
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                participation_status=HandParticipationStatus.FOLDED,
                stack_at_hand_start=STARTING_CHIPS,
            ),
            player_factory(
                player_id="player-3",
                seat=Seat.SEAT_2,
                participation_status=HandParticipationStatus.IN_HAND,
                stack_at_hand_start=STARTING_CHIPS,
            ),
        ]
        game = game_factory(players=players)

        recorder.record_game_start(game, game_metadata)
        recorder.record_hand_start(game)
        recorder.record_round_start(game)

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None
        round_record = hand.rounds[0]

        p1_state = round_record.player_records["player-1"]
        assert p1_state.participation_status == HandParticipationStatus.IN_HAND

        p2_state = round_record.player_records["player-2"]
        assert p2_state.participation_status == HandParticipationStatus.FOLDED

    def test_tracks_all_in_status(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        game_metadata: GameMetadata,
    ) -> None:
        """All-in status is captured in round player state."""
        # Player is all-in when: total_invested > 0 AND remaining_chips == 0
        players = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(0),  # No chips left
                total_invested_this_hand=STARTING_CHIPS,  # Pushed all chips in
                betting_status=BettingRoundActionStatus.ACTED,
                stack_at_hand_start=STARTING_CHIPS,
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                remaining_chips=STARTING_CHIPS,
                stack_at_hand_start=STARTING_CHIPS,
            ),
        ]
        game = game_factory(players=players)

        recorder.record_game_start(game, game_metadata)
        recorder.record_hand_start(game)
        recorder.record_round_start(game)

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None
        round_record = hand.rounds[0]

        p1_state = round_record.player_records["player-1"]
        assert p1_state.is_all_in is True

        p2_state = round_record.player_records["player-2"]
        assert p2_state.is_all_in is False

    def test_tracks_investment_across_rounds(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        game_metadata: GameMetadata,
    ) -> None:
        """Investment tracking accumulates correctly across rounds."""
        invested_preflop = ChipAmount(50)
        remaining_after_preflop = ChipAmount(950)

        players = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                remaining_chips=remaining_after_preflop,
                total_invested_this_hand=invested_preflop,
                stack_at_hand_start=STARTING_CHIPS,
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                remaining_chips=remaining_after_preflop,
                total_invested_this_hand=invested_preflop,
                stack_at_hand_start=STARTING_CHIPS,
            ),
        ]
        game = game_factory(players=players, current_phase=GamePhase.PRE_FLOP)

        recorder.record_game_start(game, game_metadata)
        recorder.record_hand_start(game)
        recorder.record_round_start(game)

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None

        round_record = hand.rounds[0]
        p1_state = round_record.player_records["player-1"]
        assert p1_state.total_invested_in_hand_at_round_start == invested_preflop

    def test_round_complete_marks_round_finished(
        self,
        recorder: Recorder,
        two_player_game: Game,
        game_metadata: GameMetadata,
    ) -> None:
        """Completing a round sets the completion timestamp."""
        recorder.record_game_start(two_player_game, game_metadata)
        recorder.record_hand_start(two_player_game)
        recorder.record_round_start(two_player_game)

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None
        round_record = hand.rounds[0]
        assert round_record.is_complete is False

        recorder.record_round_complete()

        assert round_record.is_complete is True
        assert round_record.completed_at is not None


class TestActionRecording:
    """Tests for action-level recording (record_action)."""

    def test_records_fold_action(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        game_metadata: GameMetadata,
    ) -> None:
        """Fold action is recorded with correct details."""
        players_before = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                remaining_chips=STARTING_CHIPS,
                stack_at_hand_start=STARTING_CHIPS,
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                remaining_chips=STARTING_CHIPS,
                stack_at_hand_start=STARTING_CHIPS,
            ),
        ]
        state_before = game_factory(players=players_before, pot_amount=ChipAmount(30))

        players_after = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                remaining_chips=STARTING_CHIPS,
                participation_status=HandParticipationStatus.FOLDED,
                stack_at_hand_start=STARTING_CHIPS,
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                remaining_chips=STARTING_CHIPS,
                stack_at_hand_start=STARTING_CHIPS,
            ),
        ]
        state_after = game_factory(players=players_after, pot_amount=ChipAmount(30))

        recorder.record_game_start(state_before, game_metadata)
        recorder.record_hand_start(state_before)
        recorder.record_round_start(state_before)

        fold_action = Action(action_type=ActionType.FOLD)
        response = ActionResponse(action=fold_action)
        recorder.record_action(state_before, state_after, "player-1", response)

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None
        round_record = hand.rounds[0]
        assert len(round_record.turns) == 1

        turn = round_record.turns[0]
        assert turn.action.action_type == ActionType.FOLD
        assert turn.action.player_id == "player-1"
        assert turn.action.player_name == "Alice"

    def test_records_bet_action_with_amount(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        game_metadata: GameMetadata,
    ) -> None:
        """Bet action is recorded with the bet amount."""
        bet_amount = ChipAmount(100)

        players_before = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                remaining_chips=STARTING_CHIPS,
                stack_at_hand_start=STARTING_CHIPS,
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                remaining_chips=STARTING_CHIPS,
                stack_at_hand_start=STARTING_CHIPS,
            ),
        ]
        state_before = game_factory(players=players_before, pot_amount=ChipAmount(30))

        players_after = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(900),
                total_invested_this_hand=bet_amount,
                stack_at_hand_start=STARTING_CHIPS,
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                remaining_chips=STARTING_CHIPS,
                stack_at_hand_start=STARTING_CHIPS,
            ),
        ]
        state_after = game_factory(
            players=players_after,
            pot_amount=ChipAmount(130),
        )

        recorder.record_game_start(state_before, game_metadata)
        recorder.record_hand_start(state_before)
        recorder.record_round_start(state_before)

        bet_action = Action(action_type=ActionType.BET, amount=bet_amount)
        response = ActionResponse(action=bet_action)
        recorder.record_action(state_before, state_after, "player-1", response)

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None
        turn = hand.rounds[0].turns[0]
        assert turn.action.action_type == ActionType.BET
        assert turn.action.amount == bet_amount

    def test_captures_player_state_before_action(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        game_metadata: GameMetadata,
    ) -> None:
        """Turn-level player state captures chips before the action."""
        chips_before = ChipAmount(500)

        players_before = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                remaining_chips=chips_before,
                stack_at_hand_start=chips_before,
                can_raise=True,
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                remaining_chips=STARTING_CHIPS,
                stack_at_hand_start=STARTING_CHIPS,
            ),
        ]
        state_before = game_factory(players=players_before, pot_amount=ChipAmount(0))

        players_after = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(400),
                total_invested_this_hand=ChipAmount(100),
                stack_at_hand_start=chips_before,
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                remaining_chips=STARTING_CHIPS,
                stack_at_hand_start=STARTING_CHIPS,
            ),
        ]
        state_after = game_factory(players=players_after, pot_amount=ChipAmount(100))

        recorder.record_game_start(state_before, game_metadata)
        recorder.record_hand_start(state_before)
        recorder.record_round_start(state_before)

        bet_action = Action(action_type=ActionType.BET, amount=ChipAmount(100))
        response = ActionResponse(action=bet_action)
        recorder.record_action(state_before, state_after, "player-1", response)

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None
        turn = hand.rounds[0].turns[0]

        # Player state should reflect BEFORE action
        assert turn.player_record.chips == chips_before
        assert turn.player_record.can_raise is True

    def test_records_multiple_actions_in_sequence(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        game_metadata: GameMetadata,
    ) -> None:
        """Multiple actions are recorded with correct turn numbers."""
        players = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                remaining_chips=STARTING_CHIPS,
                stack_at_hand_start=STARTING_CHIPS,
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                remaining_chips=STARTING_CHIPS,
                stack_at_hand_start=STARTING_CHIPS,
            ),
        ]
        state = game_factory(players=players, pot_amount=ChipAmount(30))

        recorder.record_game_start(state, game_metadata)
        recorder.record_hand_start(state)
        recorder.record_round_start(state)

        # First action: player-1 checks
        check_action = Action(action_type=ActionType.CHECK)
        response = ActionResponse(action=check_action)
        recorder.record_action(state, state, "player-1", response)

        # Second action: player-2 checks
        recorder.record_action(state, state, "player-2", response)

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None
        round_record = hand.rounds[0]

        assert len(round_record.turns) == 2
        assert round_record.turns[0].round_turn_number == 1
        assert round_record.turns[0].action.player_id == "player-1"
        assert round_record.turns[1].round_turn_number == 2
        assert round_record.turns[1].action.player_id == "player-2"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_operations_are_noop_when_uninitialized(
        self,
        recorder: Recorder,
        two_player_game: Game,
    ) -> None:
        """All recording operations are no-ops when record not initialized."""
        # These should not raise exceptions
        recorder.record_hand_start(two_player_game)
        recorder.record_round_start(two_player_game)
        recorder.record_round_complete()
        recorder.record_hand_complete(two_player_game)
        recorder.record_game_complete(datetime.now())

        assert recorder.record is None

    def test_hand_operations_are_noop_when_no_current_hand(
        self,
        recorder: Recorder,
        two_player_game: Game,
        game_metadata: GameMetadata,
    ) -> None:
        """Round/action operations are no-ops when no current hand exists."""
        recorder.record_game_start(two_player_game, game_metadata)
        # Don't start a hand

        # These should not raise exceptions
        recorder.record_round_start(two_player_game)
        recorder.record_round_complete()

        assert recorder.record is not None
        assert recorder.record.current_hand is None

    def test_action_recording_is_noop_when_no_current_round(
        self,
        recorder: Recorder,
        two_player_game: Game,
        game_metadata: GameMetadata,
    ) -> None:
        """Action recording is a no-op when no current round exists."""
        recorder.record_game_start(two_player_game, game_metadata)
        recorder.record_hand_start(two_player_game)
        # Don't start a round

        check_action = Action(action_type=ActionType.CHECK)
        response = ActionResponse(action=check_action)
        # Should not raise
        recorder.record_action(
            two_player_game,
            two_player_game,
            "player-1",
            response,
        )

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None
        assert len(hand.rounds) == 0

    def test_action_recording_handles_missing_player(
        self,
        recorder: Recorder,
        two_player_game: Game,
        game_metadata: GameMetadata,
    ) -> None:
        """Action recording is a no-op when player not found in game state."""
        recorder.record_game_start(two_player_game, game_metadata)
        recorder.record_hand_start(two_player_game)
        recorder.record_round_start(two_player_game)

        check_action = Action(action_type=ActionType.CHECK)
        response = ActionResponse(action=check_action)
        # Non-existent player - should not raise
        recorder.record_action(
            two_player_game,
            two_player_game,
            "non-existent-player",
            response,
        )

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None
        assert len(hand.rounds[0].turns) == 0

    def test_completes_last_round_when_hand_completes(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        game_metadata: GameMetadata,
    ) -> None:
        """Hand completion automatically completes the last round."""
        # Scenario: both players invested 50, player-2 folded, player-1 wins pot
        pot_amount = ChipAmount(100)
        invested = ChipAmount(50)
        players = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(950),  # 1000 - 50 invested
                total_invested_this_hand=invested,
                stack_at_hand_start=STARTING_CHIPS,
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(950),  # 1000 - 50 invested
                total_invested_this_hand=invested,
                participation_status=HandParticipationStatus.FOLDED,
                stack_at_hand_start=STARTING_CHIPS,
            ),
        ]
        game = game_factory(
            players=players,
            pot_amount=pot_amount,
            outcome=HandOutcome(
                hand_number=1,
                winners=[("player-1", pot_amount)],
            ),
        )

        recorder.record_game_start(game, game_metadata)
        recorder.record_hand_start(game)
        recorder.record_round_start(game)
        # Don't explicitly complete the round

        recorder.record_hand_complete(game)

        assert recorder.record is not None
        completed_hand = recorder.record.completed_hands[0]
        # The last round should be completed
        assert completed_hand.rounds[0].is_complete is True

    def test_clears_current_hand_after_completion(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        game_metadata: GameMetadata,
    ) -> None:
        """Current hand is cleared after completion."""
        pot_amount = ChipAmount(100)
        players = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1100),
                stack_at_hand_start=STARTING_CHIPS,
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(900),
                participation_status=HandParticipationStatus.FOLDED,
                stack_at_hand_start=STARTING_CHIPS,
            ),
        ]
        game = game_factory(
            players=players,
            pot_amount=pot_amount,
            outcome=HandOutcome(
                hand_number=1,
                winners=[("player-1", pot_amount)],
            ),
        )

        recorder.record_game_start(game, game_metadata)
        recorder.record_hand_start(game)
        recorder.record_hand_complete(game)

        assert recorder.record is not None
        assert recorder.record.current_hand is None
        assert len(recorder.record.completed_hands) == 1


class TestBlindPostingRecording:
    """Tests for blind posting recording (record_blind_postings)."""

    def test_records_both_blinds_in_standard_three_player_game(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        game_metadata: GameMetadata,
    ) -> None:
        """Standard 3-player game records both SB and BB postings."""
        # Pre-blind state: players have full chips, no investments
        pre_blind_players = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                remaining_chips=STARTING_CHIPS,
                total_invested_this_hand=ChipAmount(0),
                stack_at_hand_start=STARTING_CHIPS,
                hole_cards=make_hole_cards(),
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                remaining_chips=STARTING_CHIPS,
                total_invested_this_hand=ChipAmount(0),
                stack_at_hand_start=STARTING_CHIPS,
                hole_cards=make_hole_cards(),
            ),
            player_factory(
                player_id="player-3",
                seat=Seat.SEAT_2,
                remaining_chips=STARTING_CHIPS,
                total_invested_this_hand=ChipAmount(0),
                stack_at_hand_start=STARTING_CHIPS,
                hole_cards=make_hole_cards(),
            ),
        ]
        state_before = game_factory(players=pre_blind_players, button_seat=Seat.SEAT_0)

        # Post-blind state: SB (seat 1) and BB (seat 2) have posted
        post_blind_players = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                remaining_chips=STARTING_CHIPS,
                total_invested_this_hand=ChipAmount(0),
                stack_at_hand_start=STARTING_CHIPS,
                hole_cards=make_hole_cards(),
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(STARTING_CHIPS.value - SMALL_BLIND.value),
                total_invested_this_hand=SMALL_BLIND,
                stack_at_hand_start=STARTING_CHIPS,
                hole_cards=make_hole_cards(),
            ),
            player_factory(
                player_id="player-3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(STARTING_CHIPS.value - BIG_BLIND.value),
                total_invested_this_hand=BIG_BLIND,
                stack_at_hand_start=STARTING_CHIPS,
                hole_cards=make_hole_cards(),
            ),
        ]
        state_after = game_factory(players=post_blind_players, button_seat=Seat.SEAT_0)

        recorder.record_game_start(state_before, game_metadata)
        recorder.record_hand_start(state_before)
        recorder.record_round_start(state_before)
        recorder.record_blind_postings(state_before, state_after)

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None
        current_round = hand.current_round()
        assert current_round is not None
        assert len(current_round.turns) == 2

        sb_turn = current_round.turns[0]
        assert sb_turn.action.action_type == ActionType.POST_SMALL_BLIND
        assert sb_turn.action.amount == SMALL_BLIND

        bb_turn = current_round.turns[1]
        assert bb_turn.action.action_type == ActionType.POST_BIG_BLIND
        assert bb_turn.action.amount == BIG_BLIND

    def test_records_blinds_in_heads_up_game(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        game_metadata: GameMetadata,
    ) -> None:
        """Heads-up game: button is SB, other player is BB."""
        # Pre-blind state
        pre_blind_players = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                remaining_chips=STARTING_CHIPS,
                total_invested_this_hand=ChipAmount(0),
                stack_at_hand_start=STARTING_CHIPS,
                hole_cards=make_hole_cards(),
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                remaining_chips=STARTING_CHIPS,
                total_invested_this_hand=ChipAmount(0),
                stack_at_hand_start=STARTING_CHIPS,
                hole_cards=make_hole_cards(),
            ),
        ]
        state_before = game_factory(players=pre_blind_players, button_seat=Seat.SEAT_0)

        # Post-blind state: button (seat 0) is SB, seat 1 is BB
        post_blind_players = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(STARTING_CHIPS.value - SMALL_BLIND.value),
                total_invested_this_hand=SMALL_BLIND,
                stack_at_hand_start=STARTING_CHIPS,
                hole_cards=make_hole_cards(),
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(STARTING_CHIPS.value - BIG_BLIND.value),
                total_invested_this_hand=BIG_BLIND,
                stack_at_hand_start=STARTING_CHIPS,
                hole_cards=make_hole_cards(),
            ),
        ]
        state_after = game_factory(players=post_blind_players, button_seat=Seat.SEAT_0)

        recorder.record_game_start(state_before, game_metadata)
        recorder.record_hand_start(state_before)
        recorder.record_round_start(state_before)
        recorder.record_blind_postings(state_before, state_after)

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None
        current_round = hand.current_round()
        assert current_round is not None
        assert len(current_round.turns) == 2

        sb_turn = current_round.turns[0]
        assert sb_turn.action.action_type == ActionType.POST_SMALL_BLIND
        assert sb_turn.action.amount == SMALL_BLIND
        assert sb_turn.action.player_id == "player-1"

        bb_turn = current_round.turns[1]
        assert bb_turn.action.action_type == ActionType.POST_BIG_BLIND
        assert bb_turn.action.amount == BIG_BLIND
        assert bb_turn.action.player_id == "player-2"

    def test_sb_goes_all_in_with_insufficient_chips(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        game_metadata: GameMetadata,
    ) -> None:
        """SB with fewer chips than small blind posts all-in amount."""
        insufficient_chips = ChipAmount(5)  # Less than SB (10)

        # Pre-blind state
        pre_blind_players = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                remaining_chips=STARTING_CHIPS,
                total_invested_this_hand=ChipAmount(0),
                stack_at_hand_start=STARTING_CHIPS,
                hole_cards=make_hole_cards(),
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                remaining_chips=insufficient_chips,
                total_invested_this_hand=ChipAmount(0),
                stack_at_hand_start=insufficient_chips,
                hole_cards=make_hole_cards(),
            ),
            player_factory(
                player_id="player-3",
                seat=Seat.SEAT_2,
                remaining_chips=STARTING_CHIPS,
                total_invested_this_hand=ChipAmount(0),
                stack_at_hand_start=STARTING_CHIPS,
                hole_cards=make_hole_cards(),
            ),
        ]
        state_before = game_factory(players=pre_blind_players, button_seat=Seat.SEAT_0)

        # Post-blind state: SB posts all-in (5 chips)
        post_blind_players = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                remaining_chips=STARTING_CHIPS,
                total_invested_this_hand=ChipAmount(0),
                stack_at_hand_start=STARTING_CHIPS,
                hole_cards=make_hole_cards(),
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(0),
                total_invested_this_hand=insufficient_chips,
                betting_status=BettingRoundActionStatus.ACTED,
                stack_at_hand_start=insufficient_chips,
                hole_cards=make_hole_cards(),
            ),
            player_factory(
                player_id="player-3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(STARTING_CHIPS.value - BIG_BLIND.value),
                total_invested_this_hand=BIG_BLIND,
                stack_at_hand_start=STARTING_CHIPS,
                hole_cards=make_hole_cards(),
            ),
        ]
        state_after = game_factory(players=post_blind_players, button_seat=Seat.SEAT_0)

        recorder.record_game_start(state_before, game_metadata)
        recorder.record_hand_start(state_before)
        recorder.record_round_start(state_before)
        recorder.record_blind_postings(state_before, state_after)

        assert recorder.record is not None
        assert recorder.record.current_hand is not None
        current_round = recorder.record.current_hand.current_round()
        assert current_round is not None

        sb_turn = current_round.turns[0]
        assert sb_turn.action.action_type == ActionType.POST_SMALL_BLIND
        assert sb_turn.action.amount == insufficient_chips

    def test_bb_goes_all_in_with_insufficient_chips(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        game_metadata: GameMetadata,
    ) -> None:
        """BB with fewer chips than big blind posts all-in amount."""
        insufficient_chips = ChipAmount(15)  # Less than BB (20)

        # Pre-blind state
        pre_blind_players = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                remaining_chips=STARTING_CHIPS,
                total_invested_this_hand=ChipAmount(0),
                stack_at_hand_start=STARTING_CHIPS,
                hole_cards=make_hole_cards(),
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                remaining_chips=STARTING_CHIPS,
                total_invested_this_hand=ChipAmount(0),
                stack_at_hand_start=STARTING_CHIPS,
                hole_cards=make_hole_cards(),
            ),
            player_factory(
                player_id="player-3",
                seat=Seat.SEAT_2,
                remaining_chips=insufficient_chips,
                total_invested_this_hand=ChipAmount(0),
                stack_at_hand_start=insufficient_chips,
                hole_cards=make_hole_cards(),
            ),
        ]
        state_before = game_factory(players=pre_blind_players, button_seat=Seat.SEAT_0)

        # Post-blind state: BB posts all-in (15 chips)
        post_blind_players = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                remaining_chips=STARTING_CHIPS,
                total_invested_this_hand=ChipAmount(0),
                stack_at_hand_start=STARTING_CHIPS,
                hole_cards=make_hole_cards(),
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(STARTING_CHIPS.value - SMALL_BLIND.value),
                total_invested_this_hand=SMALL_BLIND,
                stack_at_hand_start=STARTING_CHIPS,
                hole_cards=make_hole_cards(),
            ),
            player_factory(
                player_id="player-3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(0),
                total_invested_this_hand=insufficient_chips,
                betting_status=BettingRoundActionStatus.ACTED,
                stack_at_hand_start=insufficient_chips,
                hole_cards=make_hole_cards(),
            ),
        ]
        state_after = game_factory(players=post_blind_players, button_seat=Seat.SEAT_0)

        recorder.record_game_start(state_before, game_metadata)
        recorder.record_hand_start(state_before)
        recorder.record_round_start(state_before)
        recorder.record_blind_postings(state_before, state_after)

        assert recorder.record is not None
        assert recorder.record.current_hand is not None
        current_round = recorder.record.current_hand.current_round()
        assert current_round is not None

        bb_turn = current_round.turns[1]
        assert bb_turn.action.action_type == ActionType.POST_BIG_BLIND
        assert bb_turn.action.amount == insufficient_chips

    def test_both_blinds_go_all_in_with_insufficient_chips(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        game_metadata: GameMetadata,
    ) -> None:
        """Both SB and BB have insufficient chips and go all-in."""
        sb_chips = ChipAmount(5)  # Less than SB (10)
        bb_chips = ChipAmount(12)  # Less than BB (20)

        pre_blind_players = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                remaining_chips=sb_chips,
                total_invested_this_hand=ChipAmount(0),
                stack_at_hand_start=sb_chips,
                hole_cards=make_hole_cards(),
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                remaining_chips=bb_chips,
                total_invested_this_hand=ChipAmount(0),
                stack_at_hand_start=bb_chips,
                hole_cards=make_hole_cards(),
            ),
        ]
        state_before = game_factory(players=pre_blind_players, button_seat=Seat.SEAT_0)

        post_blind_players = [
            player_factory(
                player_id="player-1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(0),
                total_invested_this_hand=sb_chips,
                betting_status=BettingRoundActionStatus.ACTED,
                stack_at_hand_start=sb_chips,
                hole_cards=make_hole_cards(),
            ),
            player_factory(
                player_id="player-2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(0),
                total_invested_this_hand=bb_chips,
                betting_status=BettingRoundActionStatus.ACTED,
                stack_at_hand_start=bb_chips,
                hole_cards=make_hole_cards(),
            ),
        ]
        state_after = game_factory(players=post_blind_players, button_seat=Seat.SEAT_0)

        recorder.record_game_start(state_before, game_metadata)
        recorder.record_hand_start(state_before)
        recorder.record_round_start(state_before)
        recorder.record_blind_postings(state_before, state_after)

        assert recorder.record is not None
        assert recorder.record.current_hand is not None
        current_round = recorder.record.current_hand.current_round()
        assert current_round is not None
        assert len(current_round.turns) == 2

        sb_turn = current_round.turns[0]
        assert sb_turn.action.action_type == ActionType.POST_SMALL_BLIND
        assert sb_turn.action.amount == sb_chips

        bb_turn = current_round.turns[1]
        assert bb_turn.action.action_type == ActionType.POST_BIG_BLIND
        assert bb_turn.action.amount == bb_chips
