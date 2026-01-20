"""Tests for PotCalculator - pot calculation logic."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from src.domain.models.chips import ChipAmount
from src.domain.models.player import Player
from src.domain.models.seat import Seat
from src.domain.rules.pot_calculator import PotCalculator


class TestSimpleCaseAllPlayersInvestSameAmount:
    """All players invest the same amount results in a single main pot."""

    def test_two_players_same_investment_creates_single_main_pot(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(100),
        )

        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(100),
        )

        result = PotCalculator.calculate_pot_state([player1, player2])

        assert result.main_pot.amount == ChipAmount(200)
        assert result.main_pot.eligible_player_ids == frozenset({"player-1", "player-2"})
        assert len(result.side_pots) == 0

    def test_three_players_same_investment_creates_single_main_pot(
        self, sample_player_factory: Callable[..., Player]
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
            total_invested_this_hand=ChipAmount(50),
        )

        player3 = sample_player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(50),
        )

        result = PotCalculator.calculate_pot_state([player1, player2, player3])

        assert result.main_pot.amount == ChipAmount(150)
        assert result.main_pot.eligible_player_ids == frozenset(
            {"player-1", "player-2", "player-3"}
        )
        assert len(result.side_pots) == 0

    def test_single_player_creates_single_main_pot(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(200),
        )

        result = PotCalculator.calculate_pot_state([player1])

        assert result.main_pot.amount == ChipAmount(200)
        assert result.main_pot.eligible_player_ids == frozenset({"player-1"})
        assert len(result.side_pots) == 0


class TestSidePotWithOnePlayerAllIn:
    """One player goes all-in, creating a side pot for remaining players."""

    def test_one_player_all_in_creates_main_pot_and_side_pot(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        all_in_player = sample_player_factory(
            player_id="all-in-player",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(100),
        )

        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(200),
        )

        player3 = sample_player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(200),
        )

        result = PotCalculator.calculate_pot_state([all_in_player, player2, player3])

        assert result.main_pot.amount == ChipAmount(300)
        assert result.main_pot.eligible_player_ids == frozenset(
            {"all-in-player", "player-2", "player-3"}
        )

        assert len(result.side_pots) == 1
        side_pot = result.side_pots[0]
        assert side_pot.amount == ChipAmount(200)
        assert side_pot.eligible_player_ids == frozenset({"player-2", "player-3"})

    def test_main_pot_contains_all_players_contribution_up_to_all_in_level(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        all_in_player = sample_player_factory(
            player_id="all-in-player",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(50),
        )

        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(150),
        )

        result = PotCalculator.calculate_pot_state([all_in_player, player2])

        assert result.main_pot.amount == ChipAmount(100)
        assert result.main_pot.eligible_player_ids == frozenset({"all-in-player", "player-2"})

        assert len(result.side_pots) == 1
        side_pot = result.side_pots[0]
        assert side_pot.amount == ChipAmount(100)
        assert side_pot.eligible_player_ids == frozenset({"player-2"})


class TestMultipleAllInLevels:
    """Multiple players all-in at different levels creates multiple side pots."""

    def test_three_all_in_levels_creates_main_pot_and_two_side_pots(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(100),
        )

        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(200),
        )

        player3 = sample_player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(300),
        )

        result = PotCalculator.calculate_pot_state([player1, player2, player3])

        assert result.main_pot.amount == ChipAmount(300)
        assert result.main_pot.eligible_player_ids == frozenset(
            {"player-1", "player-2", "player-3"}
        )

        assert len(result.side_pots) == 2

        first_side_pot = result.side_pots[0]
        assert first_side_pot.amount == ChipAmount(200)
        assert first_side_pot.eligible_player_ids == frozenset({"player-2", "player-3"})

        second_side_pot = result.side_pots[1]
        assert second_side_pot.amount == ChipAmount(100)
        assert second_side_pot.eligible_player_ids == frozenset({"player-3"})

    def test_four_players_with_three_all_in_levels(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(50),
        )

        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(100),
        )

        player3 = sample_player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(150),
        )

        player4 = sample_player_factory(
            player_id="player-4",
            seat=Seat.SEAT_3,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(200),
        )

        result = PotCalculator.calculate_pot_state([player1, player2, player3, player4])

        assert result.main_pot.amount == ChipAmount(200)
        assert result.main_pot.eligible_player_ids == frozenset(
            {"player-1", "player-2", "player-3", "player-4"}
        )

        assert len(result.side_pots) == 3

        first_side_pot = result.side_pots[0]
        assert first_side_pot.amount == ChipAmount(150)
        assert first_side_pot.eligible_player_ids == frozenset({"player-2", "player-3", "player-4"})

        second_side_pot = result.side_pots[1]
        assert second_side_pot.amount == ChipAmount(100)
        assert second_side_pot.eligible_player_ids == frozenset({"player-3", "player-4"})

        third_side_pot = result.side_pots[2]
        assert third_side_pot.amount == ChipAmount(50)
        assert third_side_pot.eligible_player_ids == frozenset({"player-4"})


class TestEligiblePlayerIds:
    """Verify correct players are eligible for each pot."""

    def test_player_not_eligible_for_side_pot_above_their_investment(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(100),
        )

        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(200),
        )

        result = PotCalculator.calculate_pot_state([player1, player2])

        assert "player-1" in result.main_pot.eligible_player_ids
        assert "player-2" in result.main_pot.eligible_player_ids

        assert len(result.side_pots) == 1
        assert "player-1" not in result.side_pots[0].eligible_player_ids
        assert "player-2" in result.side_pots[0].eligible_player_ids

    def test_all_players_eligible_for_main_pot_regardless_of_investment_level(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(50),
        )

        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(100),
        )

        player3 = sample_player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(200),
        )

        result = PotCalculator.calculate_pot_state([player1, player2, player3])

        assert result.main_pot.eligible_player_ids == frozenset(
            {"player-1", "player-2", "player-3"}
        )

    def test_only_highest_investors_eligible_for_highest_side_pot(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(100),
        )

        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(200),
        )

        player3 = sample_player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(300),
        )

        result = PotCalculator.calculate_pot_state([player1, player2, player3])

        highest_side_pot = result.side_pots[-1]
        assert highest_side_pot.eligible_player_ids == frozenset({"player-3"})


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_all_players_all_in_at_different_levels(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(100),
        )

        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(200),
        )

        player3 = sample_player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(300),
        )

        result = PotCalculator.calculate_pot_state([player1, player2, player3])

        assert result.main_pot.amount == ChipAmount(300)
        assert len(result.side_pots) == 2

        assert result.side_pots[0].amount == ChipAmount(200)
        assert result.side_pots[1].amount == ChipAmount(100)

    def test_zero_investment_creates_zero_pot(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(0),
        )

        result = PotCalculator.calculate_pot_state([player1])

        assert result.main_pot.amount == ChipAmount(0)
        assert result.main_pot.eligible_player_ids == frozenset({"player-1"})
        assert len(result.side_pots) == 0

    def test_empty_player_list_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Cannot calculate pot state: no players provided"):
            PotCalculator.calculate_pot_state([])

    def test_player_order_does_not_affect_pot_calculation(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(100),
        )

        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(200),
        )

        result1 = PotCalculator.calculate_pot_state([player1, player2])
        result2 = PotCalculator.calculate_pot_state([player2, player1])

        assert result1.main_pot.amount == result2.main_pot.amount
        assert result1.main_pot.eligible_player_ids == result2.main_pot.eligible_player_ids
        assert len(result1.side_pots) == len(result2.side_pots)
        if result1.side_pots:
            assert result1.side_pots[0].amount == result2.side_pots[0].amount
            assert (
                result1.side_pots[0].eligible_player_ids == result2.side_pots[0].eligible_player_ids
            )

    def test_players_with_identical_investments_share_same_pot(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(100),
        )

        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(100),
        )

        player3 = sample_player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(200),
        )

        result = PotCalculator.calculate_pot_state([player1, player2, player3])

        assert result.main_pot.amount == ChipAmount(300)
        assert result.main_pot.eligible_player_ids == frozenset(
            {"player-1", "player-2", "player-3"}
        )

        assert len(result.side_pots) == 1
        assert result.side_pots[0].amount == ChipAmount(100)
        assert result.side_pots[0].eligible_player_ids == frozenset({"player-3"})

    def test_two_players_all_in_at_same_level_creates_single_main_pot(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(100),
        )

        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(100),
        )

        result = PotCalculator.calculate_pot_state([player1, player2])

        assert result.main_pot.amount == ChipAmount(200)
        assert result.main_pot.eligible_player_ids == frozenset({"player-1", "player-2"})
        assert len(result.side_pots) == 0

    def test_three_players_all_in_at_same_level_with_fourth_higher(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(100),
        )

        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(100),
        )

        player3 = sample_player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(100),
        )

        player4 = sample_player_factory(
            player_id="player-4",
            seat=Seat.SEAT_3,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(300),
        )

        result = PotCalculator.calculate_pot_state([player1, player2, player3, player4])

        assert result.main_pot.amount == ChipAmount(400)
        assert result.main_pot.eligible_player_ids == frozenset(
            {"player-1", "player-2", "player-3", "player-4"}
        )

        assert len(result.side_pots) == 1
        assert result.side_pots[0].amount == ChipAmount(200)
        assert result.side_pots[0].eligible_player_ids == frozenset({"player-4"})


class TestPotCalculationCorrectness:
    """Verify pot amounts are calculated correctly according to poker rules."""

    def test_pot_amounts_match_expected_calculation(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(50),
        )

        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(100),
        )

        player3 = sample_player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(150),
        )

        result = PotCalculator.calculate_pot_state([player1, player2, player3])

        total_expected = ChipAmount(300)
        total_actual = result.main_pot.amount
        for side_pot in result.side_pots:
            total_actual = total_actual + side_pot.amount
        assert total_actual == total_expected

        assert result.main_pot.amount == ChipAmount(150)
        assert result.side_pots[0].amount == ChipAmount(100)
        assert result.side_pots[1].amount == ChipAmount(50)

    def test_large_investment_amounts_calculate_correctly(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(1000),
        )

        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(5000),
        )

        player3 = sample_player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=ChipAmount(10000),
            total_invested_this_hand=ChipAmount(10000),
        )

        result = PotCalculator.calculate_pot_state([player1, player2, player3])

        total_expected = ChipAmount(16000)
        total_actual = result.main_pot.amount
        for side_pot in result.side_pots:
            total_actual = total_actual + side_pot.amount
        assert total_actual == total_expected

        assert result.main_pot.amount == ChipAmount(3000)
        assert len(result.side_pots) == 2
        assert result.side_pots[0].amount == ChipAmount(8000)
        assert result.side_pots[1].amount == ChipAmount(5000)
