"""Behavioral tests for Game hand and round completion logic."""

from __future__ import annotations

from collections.abc import Callable

from src.domain.models.chips import ChipAmount
from src.domain.models.game import Game, GamePhase
from src.domain.models.player import (BettingRoundActionStatus,
                                      HandParticipationStatus, Player)
from src.domain.models.seat import Seat

from .conftest import (BIG_BLIND_STANDARD, LARGE_CHIPS, MEDIUM_CHIPS,
                       SMALL_BLIND_STANDARD, ZERO_CHIPS)


class TestIsHandComplete:
    """Tests for Game.is_hand_complete() method.

    A hand is complete when:
    1. We've reached showdown phase → betting complete, proceed to determine winners
    2. Only one player remains (all others folded) → early win, no showdown needed
    """

    def test_returns_true_when_phase_is_showdown_regardless_of_player_count(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat(0),
            remaining_chips=MEDIUM_CHIPS,
            participation_status=HandParticipationStatus.IN_HAND,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat(1),
            remaining_chips=MEDIUM_CHIPS,
            participation_status=HandParticipationStatus.IN_HAND,
        )
        player3 = sample_player_factory(
            player_id="player-3",
            seat=Seat(2),
            remaining_chips=MEDIUM_CHIPS,
            participation_status=HandParticipationStatus.IN_HAND,
        )

        game = minimal_game_factory(
            players=[player1, player2, player3],
            current_phase=GamePhase.SHOWDOWN,
        )

        assert game.is_hand_complete() is True

    def test_returns_true_when_only_one_player_remains_in_hand(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat(0),
            remaining_chips=MEDIUM_CHIPS,
            participation_status=HandParticipationStatus.IN_HAND,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat(1),
            remaining_chips=MEDIUM_CHIPS,
            participation_status=HandParticipationStatus.FOLDED,
        )
        player3 = sample_player_factory(
            player_id="player-3",
            seat=Seat(2),
            remaining_chips=MEDIUM_CHIPS,
            participation_status=HandParticipationStatus.FOLDED,
        )

        game = minimal_game_factory(
            players=[player1, player2, player3],
            current_phase=GamePhase.PRE_FLOP,
        )

        assert game.is_hand_complete() is True

    def test_returns_false_when_multiple_players_remain_and_phase_is_not_showdown(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat(0),
            remaining_chips=MEDIUM_CHIPS,
            participation_status=HandParticipationStatus.IN_HAND,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat(1),
            remaining_chips=MEDIUM_CHIPS,
            participation_status=HandParticipationStatus.IN_HAND,
        )
        player3 = sample_player_factory(
            player_id="player-3",
            seat=Seat(2),
            remaining_chips=MEDIUM_CHIPS,
            participation_status=HandParticipationStatus.IN_HAND,
        )

        for phase in [GamePhase.PRE_FLOP, GamePhase.FLOP, GamePhase.TURN, GamePhase.RIVER]:
            game = minimal_game_factory(
                players=[player1, player2, player3],
                current_phase=phase,
            )
            assert game.is_hand_complete() is False, f"Hand should not be complete in {phase} phase"

    def test_returns_false_when_two_players_remain_in_pre_flop(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat(0),
            remaining_chips=MEDIUM_CHIPS,
            participation_status=HandParticipationStatus.IN_HAND,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat(1),
            remaining_chips=MEDIUM_CHIPS,
            participation_status=HandParticipationStatus.IN_HAND,
        )

        game = minimal_game_factory(
            players=[player1, player2],
            current_phase=GamePhase.PRE_FLOP,
        )

        assert game.is_hand_complete() is False

    def test_handles_eliminated_players_correctly(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat(0),
            remaining_chips=MEDIUM_CHIPS,
            participation_status=HandParticipationStatus.IN_HAND,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat(1),
            remaining_chips=MEDIUM_CHIPS,
            participation_status=HandParticipationStatus.ELIMINATED,
        )
        player3 = sample_player_factory(
            player_id="player-3",
            seat=Seat(2),
            remaining_chips=MEDIUM_CHIPS,
            participation_status=HandParticipationStatus.FOLDED,
        )

        game = minimal_game_factory(
            players=[player1, player2, player3],
            current_phase=GamePhase.PRE_FLOP,
        )

        assert game.is_hand_complete() is True


class TestIsRoundComplete:
    """Tests for Game.is_round_complete() method.

    A betting round is complete when:
    1. If only 1 player remains (not folded) → hand ends → round complete
    2. If all players in hand have acted AND investments are equal → round complete
    3. If all players in hand are all-in → round complete (no more betting)
    4. Otherwise → round continues
    """

    def test_returns_true_when_only_one_player_remains_in_hand(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat(0),
            remaining_chips=MEDIUM_CHIPS,
            participation_status=HandParticipationStatus.IN_HAND,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat(1),
            remaining_chips=MEDIUM_CHIPS,
            participation_status=HandParticipationStatus.FOLDED,
        )

        game = minimal_game_factory(players=[player1, player2])

        assert game.is_round_complete() is True

    def test_returns_true_when_all_players_have_acted_and_investments_are_equal(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        equal_investment = BIG_BLIND_STANDARD
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat(0),
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=equal_investment,
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat(1),
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=equal_investment,
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        player3 = sample_player_factory(
            player_id="player-3",
            seat=Seat(2),
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=equal_investment,
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )

        game = minimal_game_factory(players=[player1, player2, player3])

        assert game.is_round_complete() is True

    def test_returns_true_when_all_players_are_all_in(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat(0),
            remaining_chips=ZERO_CHIPS,
            total_invested_this_hand=MEDIUM_CHIPS,
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat(1),
            remaining_chips=ZERO_CHIPS,
            total_invested_this_hand=LARGE_CHIPS,
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )

        game = minimal_game_factory(players=[player1, player2])

        assert game.is_round_complete() is True

    def test_returns_false_when_player_needs_to_call(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat(0),
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat(1),
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=SMALL_BLIND_STANDARD,
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )

        game = minimal_game_factory(players=[player1, player2])

        assert game.is_round_complete() is False

    def test_returns_false_when_player_has_not_acted_this_round(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        equal_investment = BIG_BLIND_STANDARD
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat(0),
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=equal_investment,
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat(1),
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=equal_investment,
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )

        game = minimal_game_factory(players=[player1, player2])

        assert game.is_round_complete() is False

    def test_returns_false_when_player_needs_to_call_and_has_not_acted(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat(0),
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat(1),
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=SMALL_BLIND_STANDARD,
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )

        game = minimal_game_factory(players=[player1, player2])

        assert game.is_round_complete() is False

    def test_returns_true_when_mix_of_all_in_and_acted_players_with_equal_investments(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        equal_investment = BIG_BLIND_STANDARD
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat(0),
            remaining_chips=ZERO_CHIPS,
            total_invested_this_hand=equal_investment,
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat(1),
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=equal_investment,
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )

        game = minimal_game_factory(players=[player1, player2])

        assert game.is_round_complete() is True

    def test_returns_true_when_all_in_player_has_less_investment_and_other_player_has_acted_with_max(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat(0),
            remaining_chips=ZERO_CHIPS,
            total_invested_this_hand=SMALL_BLIND_STANDARD,
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat(1),
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )

        game = minimal_game_factory(players=[player1, player2])

        assert game.is_round_complete() is True

    def test_returns_false_when_player_with_chips_has_not_acted_and_investments_are_unequal(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat(0),
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat(1),
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=SMALL_BLIND_STANDARD,
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )

        game = minimal_game_factory(players=[player1, player2])

        assert game.is_round_complete() is False

    def test_returns_true_when_all_players_have_acted_with_zero_investments(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat(0),
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=ZERO_CHIPS,
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat(1),
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=ZERO_CHIPS,
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )

        game = minimal_game_factory(players=[player1, player2])

        assert game.is_round_complete() is True

    def test_handles_three_players_with_mixed_states_correctly(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        equal_investment = ChipAmount(50)
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat(0),
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=equal_investment,
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat(1),
            remaining_chips=ZERO_CHIPS,
            total_invested_this_hand=equal_investment,
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        player3 = sample_player_factory(
            player_id="player-3",
            seat=Seat(2),
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=equal_investment,
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )

        game = minimal_game_factory(players=[player1, player2, player3])

        assert game.is_round_complete() is True

    def test_returns_false_when_one_player_needs_to_call_in_three_player_game(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat(0),
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=ChipAmount(100),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat(1),
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        player3 = sample_player_factory(
            player_id="player-3",
            seat=Seat(2),
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )

        game = minimal_game_factory(players=[player1, player2, player3])

        assert game.is_round_complete() is False
