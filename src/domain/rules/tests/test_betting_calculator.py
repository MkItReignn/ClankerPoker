"""Tests for BettingCalculator - pure calculation logic."""

from __future__ import annotations

from collections.abc import Callable

from src.domain.models.chips import ChipAmount
from src.domain.models.game import Game
from src.domain.models.player import BettingRoundActionStatus, HandParticipationStatus, Player
from src.domain.models.seat import Seat
from src.domain.rules.betting_calculator import BettingCalculator

from .conftest import BIG_BLIND_STANDARD, MEDIUM_CHIPS, ZERO_CHIPS


class TestCalculateMinimumRaiseIncrement:
    """Tests for calculate_minimum_raise_increment method."""

    def test_first_raise_uses_big_blind_when_no_previous_raise(self) -> None:
        last_raise_increment = ZERO_CHIPS
        big_blind = BIG_BLIND_STANDARD

        result = BettingCalculator.calculate_minimum_raise_increment(
            last_raise_increment, big_blind
        )

        assert result == big_blind

    def test_re_raise_uses_last_increment_when_greater_than_big_blind(self) -> None:
        last_raise_increment = MEDIUM_CHIPS
        big_blind = BIG_BLIND_STANDARD

        result = BettingCalculator.calculate_minimum_raise_increment(
            last_raise_increment, big_blind
        )

        assert result == last_raise_increment

    def test_re_raise_uses_big_blind_when_last_increment_less_than_big_blind(self) -> None:
        last_raise_increment = ChipAmount(15)
        big_blind = BIG_BLIND_STANDARD

        result = BettingCalculator.calculate_minimum_raise_increment(
            last_raise_increment, big_blind
        )

        assert result == big_blind

    def test_re_raise_uses_last_increment_when_equal_to_big_blind(self) -> None:
        last_raise_increment = BIG_BLIND_STANDARD
        big_blind = BIG_BLIND_STANDARD

        result = BettingCalculator.calculate_minimum_raise_increment(
            last_raise_increment, big_blind
        )

        assert result == last_raise_increment


class TestCalculateCallAmount:
    """Tests for calculate_call_amount method."""

    def test_normal_call_returns_difference(self) -> None:
        max_invested_this_hand = ChipAmount(100)
        player_invested_this_hand = ChipAmount(20)

        result = BettingCalculator.calculate_call_amount(
            max_invested_this_hand, player_invested_this_hand
        )

        assert result == ChipAmount(80)

    def test_call_amount_not_capped_by_available_chips(self) -> None:
        max_invested_this_hand = ChipAmount(100)
        player_invested_this_hand = ChipAmount(20)

        result = BettingCalculator.calculate_call_amount(
            max_invested_this_hand, player_invested_this_hand
        )

        assert result == ChipAmount(80)

    def test_zero_call_when_player_already_matched(self) -> None:
        max_invested_this_hand = ChipAmount(100)
        player_invested_this_hand = ChipAmount(100)

        result = BettingCalculator.calculate_call_amount(
            max_invested_this_hand, player_invested_this_hand
        )

        assert result == ChipAmount(0)

    def test_zero_call_when_player_invested_exceeds_max(self) -> None:
        max_invested_this_hand = ChipAmount(100)
        player_invested_this_hand = ChipAmount(150)

        result = BettingCalculator.calculate_call_amount(
            max_invested_this_hand, player_invested_this_hand
        )

        assert result == ChipAmount(0)

    def test_call_with_zero_max_invested(self) -> None:
        max_invested_this_hand = ChipAmount(0)
        player_invested_this_hand = ChipAmount(0)

        result = BettingCalculator.calculate_call_amount(
            max_invested_this_hand, player_invested_this_hand
        )

        assert result == ChipAmount(0)


class TestGetMaxInvestedThisHand:
    """Tests for get_max_invested_this_hand method."""

    def test_single_player_in_hand_returns_their_investment(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(50),
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(0),
            participation_status=HandParticipationStatus.FOLDED,
        )
        game = minimal_game_factory([player1, player2])

        result = BettingCalculator.get_max_invested_this_hand(game.players_in_hand())

        assert result == ChipAmount(50)

    def test_multiple_players_returns_maximum_investment(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(20),
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(100),
        )
        player3 = sample_player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(50),
        )
        game = minimal_game_factory([player1, player2, player3])

        result = BettingCalculator.get_max_invested_this_hand(game.players_in_hand())

        assert result == ChipAmount(100)

    def test_ignores_folded_players(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(100),
            participation_status=HandParticipationStatus.FOLDED,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(50),
        )
        game = minimal_game_factory([player1, player2])

        result = BettingCalculator.get_max_invested_this_hand(game.players_in_hand())

        assert result == ChipAmount(50)

    def test_ignores_eliminated_players(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(200),
            participation_status=HandParticipationStatus.ELIMINATED,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(75),
        )
        game = minimal_game_factory([player1, player2])

        result = BettingCalculator.get_max_invested_this_hand(game.players_in_hand())

        assert result == ChipAmount(75)

    def test_all_in_scenario_returns_all_in_amount(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(500),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(100),
        )
        game = minimal_game_factory([player1, player2])

        result = BettingCalculator.get_max_invested_this_hand(game.players_in_hand())

        assert result == ChipAmount(500)

    def test_returns_zero_when_no_players_in_hand(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(100),
            participation_status=HandParticipationStatus.FOLDED,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(50),
            participation_status=HandParticipationStatus.FOLDED,
        )
        game = minimal_game_factory([player1, player2])

        result = BettingCalculator.get_max_invested_this_hand(game.players_in_hand())

        assert result == ChipAmount(0)

    def test_handles_players_with_zero_current_bet(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(0),
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(0),
        )
        game = minimal_game_factory([player1, player2])

        result = BettingCalculator.get_max_invested_this_hand(game.players_in_hand())

        assert result == ChipAmount(0)
