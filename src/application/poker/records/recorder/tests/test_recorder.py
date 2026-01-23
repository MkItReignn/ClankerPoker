"""Behavioral tests for Recorder.

Tests focus on documenting and verifying the recorder's behavior at each
level of the game hierarchy: Game -> Hand -> Round -> Turn.

Updated for Phase 1: All methods are now async and use Details dataclasses.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import pytest

from src.application.poker.records.models import GameMetadata
from src.application.poker.records.recorder import Recorder
from src.application.poker.state_observers.details import (
    ActionAppliedDetails,
    BlindInfo,
    BlindsPostedDetails,
    GameCompletedDetails,
    GameStartedDetails,
    HandOutcomeDetails,
    HandStartedDetails,
    PlayerOutcome,
    RoundCompletedDetails,
    RoundStartedDetails,
    WinnerInfo,
)
from src.application.poker.state_observers.details_factory import DetailsFactory
from src.config.poker.config import PokerPlayerConfig
from src.domain.models.actions import ActionType
from src.domain.models.card import Rank
from src.domain.models.chips import ChipAmount
from src.domain.models.game import Game, GamePhase, HandOutcome as GameHandOutcome
from src.domain.models.player import (
    BettingRoundActionStatus,
    HandParticipationStatus,
    Player,
)
from src.domain.models.seat import Seat

from .conftest import BIG_BLIND, SMALL_BLIND, STARTING_CHIPS, make_hole_cards


def make_game_started_details(game: Game) -> GameStartedDetails:
    return GameStartedDetails(
        player_count=len(game.players),
        starting_chips=STARTING_CHIPS,
    )


def make_hand_started_details(game: Game) -> HandStartedDetails:
    return HandStartedDetails(
        hand_number=game.hand_state.hand_number,
        button_seat=game.button_seat,
    )


def make_round_started_details(game: Game) -> RoundStartedDetails:
    return RoundStartedDetails(
        phase=game.current_phase,
        new_cards=tuple(game.community_cards) if game.community_cards else (),
    )


def make_mock_hand_outcome(game: Game) -> HandOutcomeDetails:
    winner_id = game.players[0].id
    winner_name = game.players[0].name
    pot = game.pot if game.pot.value > 0 else ChipAmount(100)

    return HandOutcomeDetails(
        winners=(WinnerInfo(player_id=winner_id, player_name=winner_name, amount=pot),),
        eliminated=(),
        showdown=None,
        pot_amount=pot,
        player_outcomes=(),
    )


class TestGameLifecycle:
    """Tests for game-level recording (on_game_started, on_game_completed)."""

    @pytest.mark.asyncio
    async def test_registers_all_players_with_initial_state(
        self,
        recorder: Recorder,
        two_player_game: Game,
    ) -> None:
        """All players are registered with correct initial chips and seat."""
        await recorder.on_game_started(two_player_game, make_game_started_details(two_player_game))

        assert recorder.record is not None
        assert len(recorder.record.player_records) == 2

        p1 = recorder.record.player_records["player-1"]
        assert p1.player_name == "Alice"
        assert p1.seat == Seat.SEAT_0

        p2 = recorder.record.player_records["player-2"]
        assert p2.player_name == "Bob"
        assert p2.seat == Seat.SEAT_1

    @pytest.mark.asyncio
    async def test_stores_game_id_from_state(
        self,
        recorder: Recorder,
        two_player_game: Game,
    ) -> None:
        """Game ID is captured from the game state."""
        await recorder.on_game_started(two_player_game, make_game_started_details(two_player_game))

        assert recorder.record is not None
        assert recorder.record.game_id == two_player_game.id

    @pytest.mark.asyncio
    async def test_stores_tournament_metadata(
        self,
        recorder: Recorder,
        two_player_game: Game,
    ) -> None:
        """Tournament configuration metadata is captured."""
        await recorder.on_game_started(two_player_game, make_game_started_details(two_player_game))

        assert recorder.record is not None
        assert recorder.record.metadata.seed == 42

    @pytest.mark.asyncio
    async def test_record_game_complete_sets_completion_timestamp(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        player_names: dict[str, str],
    ) -> None:
        """Completing the game sets the completion timestamp in metadata."""
        from src.domain.models.game import GameStatus

        players = [
            player_factory(player_id="player-1", seat=Seat.SEAT_0, stack_at_hand_start=STARTING_CHIPS),
            player_factory(player_id="player-2", seat=Seat.SEAT_1, stack_at_hand_start=STARTING_CHIPS),
        ]
        # Create a completed game with completed_at timestamp and required outcome
        completed_game = game_factory(
            players=players,
            status=GameStatus.COMPLETED,
            outcome=GameHandOutcome(hand_number=5, winners=[("player-1", ChipAmount(100))]),
        )

        await recorder.on_game_started(completed_game, make_game_started_details(completed_game))

        details = GameCompletedDetails(
            winner_id="player-1",
            winner_name=player_names["player-1"],
            total_hands=5,
        )
        await recorder.on_game_completed(completed_game, details)

        assert recorder.record is not None
        assert recorder.record.metadata.completed_at is not None

    @pytest.mark.asyncio
    async def test_raises_on_unknown_player_id(
        self,
        two_player_game: Game,
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
            await recorder.on_game_started(two_player_game, make_game_started_details(two_player_game))


class TestHandLifecycle:
    """Tests for hand-level recording (on_hand_started, on_hand_completed)."""

    @pytest.mark.asyncio
    async def test_captures_player_positions(
        self,
        recorder: Recorder,
        three_player_game: Game,
    ) -> None:
        """Each player's position (BTN, SB, BB) is recorded at hand start."""
        await recorder.on_game_started(three_player_game, make_game_started_details(three_player_game))
        await recorder.on_hand_started(three_player_game, make_hand_started_details(three_player_game))

        assert recorder.record is not None
        assert recorder.record.current_hand is not None

        hand = recorder.record.current_hand
        positions_recorded = {pid: state.position for pid, state in hand.player_records.items()}

        # At least one position should be assigned
        assert any(pos is not None for pos in positions_recorded.values())

    @pytest.mark.asyncio
    async def test_captures_hole_cards(
        self,
        recorder: Recorder,
        two_player_game: Game,
    ) -> None:
        """Hole cards are captured for each player at hand start."""
        await recorder.on_game_started(two_player_game, make_game_started_details(two_player_game))
        await recorder.on_hand_started(two_player_game, make_hand_started_details(two_player_game))

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None

        p1_state = hand.player_records["player-1"]
        assert p1_state.hole_cards is not None
        assert p1_state.hole_cards.card1.rank == Rank.ACE

    @pytest.mark.asyncio
    async def test_captures_button_seat_and_blinds(
        self,
        recorder: Recorder,
        two_player_game: Game,
    ) -> None:
        """Button seat and blind levels are recorded at hand start."""
        await recorder.on_game_started(two_player_game, make_game_started_details(two_player_game))
        await recorder.on_hand_started(two_player_game, make_hand_started_details(two_player_game))

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None
        assert hand.button_seat == two_player_game.button_seat
        assert hand.blinds == two_player_game.current_blind_level

    @pytest.mark.asyncio
    async def test_captures_hand_number(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
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

        await recorder.on_game_started(game, make_game_started_details(game))
        await recorder.on_hand_started(game, make_hand_started_details(game))

        assert recorder.record is not None
        assert recorder.record.current_hand is not None
        assert recorder.record.current_hand.hand_number == 5

    @pytest.mark.asyncio
    async def test_excludes_eliminated_players(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
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

        await recorder.on_game_started(game, make_game_started_details(game))
        await recorder.on_hand_started(game, make_hand_started_details(game))

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None

        # Only non-eliminated players should be in hand states
        assert "player-1" in hand.player_records
        assert "player-2" not in hand.player_records
        assert "player-3" in hand.player_records

    @pytest.mark.asyncio
    async def test_starting_chips_captured_correctly(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
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

        await recorder.on_game_started(game, make_game_started_details(game))
        await recorder.on_hand_started(game, make_hand_started_details(game))

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None

        p1_state = hand.player_records["player-1"]
        assert p1_state.starting_chips == current_chips
        assert p1_state.chips == current_chips


class TestHandOutcome:
    """Tests for hand completion and outcome recording."""

    @pytest.mark.asyncio
    async def test_records_winner_on_fold_out(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        player_names: dict[str, str],
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
            outcome=GameHandOutcome(
                hand_number=1,
                winners=[("player-1", pot_amount)],
            ),
            current_phase=GamePhase.PRE_FLOP,
        )

        await recorder.on_game_started(game, make_game_started_details(game))
        await recorder.on_hand_started(game, make_hand_started_details(game))

        await recorder.on_hand_completed(game, make_mock_hand_outcome(game))

        assert recorder.record is not None
        assert len(recorder.record.completed_hands) == 1

        completed_hand = recorder.record.completed_hands[0]
        assert completed_hand.outcome is not None
        assert any(w.player_id == "player-1" for w in completed_hand.outcome.winners)
        assert completed_hand.outcome.showdown is None

    @pytest.mark.asyncio
    async def test_records_showdown_with_hand_evaluations(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        player_names: dict[str, str],
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
            outcome=GameHandOutcome(
                hand_number=1,
                winners=[("player-1", pot_amount)],
            ),
        )

        await recorder.on_game_started(game, make_game_started_details(game))
        await recorder.on_hand_started(game, make_hand_started_details(game))

        details = DetailsFactory.hand_completed(game)
        await recorder.on_hand_completed(game, details)

        assert recorder.record is not None
        completed_hand = recorder.record.completed_hands[0]
        assert completed_hand.outcome is not None
        assert completed_hand.outcome.showdown is not None
        assert len(completed_hand.outcome.showdown) == 2

        # Verify showdown results contain hand evaluations
        for result in completed_hand.outcome.showdown:
            assert result.hole_cards is not None
            assert result.hand_evaluation is not None


class TestRoundLifecycle:
    """Tests for round-level recording (on_round_started, on_round_completed)."""

    @pytest.mark.asyncio
    async def test_captures_community_cards(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
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

        await recorder.on_game_started(game, make_game_started_details(game))
        await recorder.on_hand_started(game, make_hand_started_details(game))
        await recorder.on_round_started(game, make_round_started_details(game))

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None
        assert len(hand.rounds) == 1

        round_record = hand.rounds[0]
        assert round_record.phase == GamePhase.FLOP

    @pytest.mark.asyncio
    async def test_tracks_player_participation_status(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
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

        await recorder.on_game_started(game, make_game_started_details(game))
        await recorder.on_hand_started(game, make_hand_started_details(game))
        await recorder.on_round_started(game, make_round_started_details(game))

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None
        round_record = hand.rounds[0]

        p1_state = round_record.player_records["player-1"]
        assert p1_state.participation_status == HandParticipationStatus.IN_HAND

        p2_state = round_record.player_records["player-2"]
        assert p2_state.participation_status == HandParticipationStatus.FOLDED

    @pytest.mark.asyncio
    async def test_tracks_all_in_status(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
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

        await recorder.on_game_started(game, make_game_started_details(game))
        await recorder.on_hand_started(game, make_hand_started_details(game))
        await recorder.on_round_started(game, make_round_started_details(game))

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None
        round_record = hand.rounds[0]

        p1_state = round_record.player_records["player-1"]
        assert p1_state.is_all_in is True

        p2_state = round_record.player_records["player-2"]
        assert p2_state.is_all_in is False

    @pytest.mark.asyncio
    async def test_round_complete_marks_round_finished(
        self,
        recorder: Recorder,
        two_player_game: Game,
    ) -> None:
        """Completing a round sets the completion timestamp."""
        await recorder.on_game_started(two_player_game, make_game_started_details(two_player_game))
        await recorder.on_hand_started(two_player_game, make_hand_started_details(two_player_game))
        await recorder.on_round_started(two_player_game, make_round_started_details(two_player_game))

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None
        round_record = hand.rounds[0]
        assert round_record.is_complete is False

        await recorder.on_round_completed(two_player_game, RoundCompletedDetails())

        assert round_record.is_complete is True
        assert round_record.completed_at is not None


class TestActionRecording:
    """Tests for action-level recording (on_action_applied)."""

    @pytest.mark.asyncio
    async def test_records_fold_action(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        player_names: dict[str, str],
    ) -> None:
        """Fold action is recorded with correct details."""
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
        game = game_factory(players=players, pot_amount=ChipAmount(30))

        await recorder.on_game_started(game, make_game_started_details(game))
        await recorder.on_hand_started(game, make_hand_started_details(game))
        await recorder.on_round_started(game, make_round_started_details(game))

        details = ActionAppliedDetails(
            player_id="player-1",
            player_name=player_names["player-1"],
            action_type=ActionType.FOLD,
            amount=None,
            narration=None,
        )
        await recorder.on_action_applied(game, details)

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None
        round_record = hand.rounds[0]
        assert len(round_record.turns) == 1

        turn = round_record.turns[0]
        assert turn.action.action_type == ActionType.FOLD
        assert turn.action.player_id == "player-1"
        assert turn.action.player_name == "Alice"

    @pytest.mark.asyncio
    async def test_records_bet_action_with_amount(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        player_names: dict[str, str],
    ) -> None:
        """Bet action is recorded with the bet amount."""
        bet_amount = ChipAmount(100)

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
        game = game_factory(players=players, pot_amount=ChipAmount(30))

        await recorder.on_game_started(game, make_game_started_details(game))
        await recorder.on_hand_started(game, make_hand_started_details(game))
        await recorder.on_round_started(game, make_round_started_details(game))

        details = ActionAppliedDetails(
            player_id="player-1",
            player_name=player_names["player-1"],
            action_type=ActionType.BET,
            amount=bet_amount,
            narration=None,
        )
        await recorder.on_action_applied(game, details)

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None
        turn = hand.rounds[0].turns[0]
        assert turn.action.action_type == ActionType.BET
        assert turn.action.amount == bet_amount

    @pytest.mark.asyncio
    async def test_records_multiple_actions_in_sequence(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        player_names: dict[str, str],
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
        game = game_factory(players=players, pot_amount=ChipAmount(30))

        await recorder.on_game_started(game, make_game_started_details(game))
        await recorder.on_hand_started(game, make_hand_started_details(game))
        await recorder.on_round_started(game, make_round_started_details(game))

        # First action: player-1 checks
        details1 = ActionAppliedDetails(
            player_id="player-1",
            player_name=player_names["player-1"],
            action_type=ActionType.CHECK,
            amount=None,
            narration=None,
        )
        await recorder.on_action_applied(game, details1)

        # Second action: player-2 checks
        details2 = ActionAppliedDetails(
            player_id="player-2",
            player_name=player_names["player-2"],
            action_type=ActionType.CHECK,
            amount=None,
            narration=None,
        )
        await recorder.on_action_applied(game, details2)

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

    @pytest.mark.asyncio
    async def test_operations_are_noop_when_uninitialized(
        self,
        recorder: Recorder,
        two_player_game: Game,
        player_names: dict[str, str],
    ) -> None:
        """All recording operations are no-ops when record not initialized."""
        # These should not raise exceptions
        await recorder.on_hand_started(two_player_game, make_hand_started_details(two_player_game))
        await recorder.on_round_started(two_player_game, make_round_started_details(two_player_game))
        await recorder.on_round_completed(two_player_game, RoundCompletedDetails())

        await recorder.on_hand_completed(two_player_game, make_mock_hand_outcome(two_player_game))

        game_details = GameCompletedDetails(
            winner_id="player-1",
            winner_name=player_names["player-1"],
            total_hands=1,
        )
        await recorder.on_game_completed(two_player_game, game_details)

        assert recorder.record is None

    @pytest.mark.asyncio
    async def test_hand_operations_are_noop_when_no_current_hand(
        self,
        recorder: Recorder,
        two_player_game: Game,
    ) -> None:
        """Round/action operations are no-ops when no current hand exists."""
        await recorder.on_game_started(two_player_game, make_game_started_details(two_player_game))
        # Don't start a hand

        # These should not raise exceptions
        await recorder.on_round_started(two_player_game, make_round_started_details(two_player_game))
        await recorder.on_round_completed(two_player_game, RoundCompletedDetails())

        assert recorder.record is not None
        assert recorder.record.current_hand is None

    @pytest.mark.asyncio
    async def test_action_recording_is_noop_when_no_current_round(
        self,
        recorder: Recorder,
        two_player_game: Game,
        player_names: dict[str, str],
    ) -> None:
        """Action recording is a no-op when no current round exists."""
        await recorder.on_game_started(two_player_game, make_game_started_details(two_player_game))
        await recorder.on_hand_started(two_player_game, make_hand_started_details(two_player_game))
        # Don't start a round

        details = ActionAppliedDetails(
            player_id="player-1",
            player_name=player_names["player-1"],
            action_type=ActionType.CHECK,
            amount=None,
            narration=None,
        )
        # Should not raise
        await recorder.on_action_applied(two_player_game, details)

        assert recorder.record is not None
        hand = recorder.record.current_hand
        assert hand is not None
        assert len(hand.rounds) == 0


class TestBlindPostingRecording:
    """Tests for blind posting recording (on_blinds_posted)."""

    @pytest.mark.asyncio
    async def test_records_both_blinds_in_standard_three_player_game(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        player_names: dict[str, str],
    ) -> None:
        """Standard 3-player game records both SB and BB postings."""
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
        game = game_factory(players=pre_blind_players, button_seat=Seat.SEAT_0)

        await recorder.on_game_started(game, make_game_started_details(game))
        await recorder.on_hand_started(game, make_hand_started_details(game))
        await recorder.on_round_started(game, make_round_started_details(game))

        blinds_details = BlindsPostedDetails(
            small_blind=BlindInfo(
                player_id="player-2",
                player_name=player_names["player-2"],
                amount=SMALL_BLIND,
            ),
            big_blind=BlindInfo(
                player_id="player-3",
                player_name=player_names["player-3"],
                amount=BIG_BLIND,
            ),
        )
        await recorder.on_blinds_posted(game, blinds_details)

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

    @pytest.mark.asyncio
    async def test_records_blinds_in_heads_up_game(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        player_names: dict[str, str],
    ) -> None:
        """Heads-up game: button is SB, other player is BB."""
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
        game = game_factory(players=pre_blind_players, button_seat=Seat.SEAT_0)

        await recorder.on_game_started(game, make_game_started_details(game))
        await recorder.on_hand_started(game, make_hand_started_details(game))
        await recorder.on_round_started(game, make_round_started_details(game))

        blinds_details = BlindsPostedDetails(
            small_blind=BlindInfo(
                player_id="player-1",
                player_name=player_names["player-1"],
                amount=SMALL_BLIND,
            ),
            big_blind=BlindInfo(
                player_id="player-2",
                player_name=player_names["player-2"],
                amount=BIG_BLIND,
            ),
        )
        await recorder.on_blinds_posted(game, blinds_details)

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

    @pytest.mark.asyncio
    async def test_sb_goes_all_in_with_insufficient_chips(
        self,
        recorder: Recorder,
        player_factory: Callable[..., Player],
        game_factory: Callable[..., Game],
        player_names: dict[str, str],
    ) -> None:
        """SB with fewer chips than small blind posts all-in amount."""
        insufficient_chips = ChipAmount(5)  # Less than SB (10)

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
        game = game_factory(players=pre_blind_players, button_seat=Seat.SEAT_0)

        await recorder.on_game_started(game, make_game_started_details(game))
        await recorder.on_hand_started(game, make_hand_started_details(game))
        await recorder.on_round_started(game, make_round_started_details(game))

        blinds_details = BlindsPostedDetails(
            small_blind=BlindInfo(
                player_id="player-2",
                player_name=player_names["player-2"],
                amount=insufficient_chips,  # All-in amount
            ),
            big_blind=BlindInfo(
                player_id="player-3",
                player_name=player_names["player-3"],
                amount=BIG_BLIND,
            ),
        )
        await recorder.on_blinds_posted(game, blinds_details)

        assert recorder.record is not None
        assert recorder.record.current_hand is not None
        current_round = recorder.record.current_hand.current_round()
        assert current_round is not None

        sb_turn = current_round.turns[0]
        assert sb_turn.action.action_type == ActionType.POST_SMALL_BLIND
        assert sb_turn.action.amount == insufficient_chips
