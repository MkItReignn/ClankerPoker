"""Tests for ChipDistributor - chip distribution logic.

Tests follow Rule Book invariants:
- Section 9.4: Side Pot Awarding (fewest eligible players first)
- Section 12.2-12.3: Split Pots and Odd Chip Rule
- Section 12.6: Uncalled Bet Returns
"""

from collections.abc import Callable

from src.domain.models.chips import ChipAmount
from src.domain.models.player import Player
from src.domain.models.pot import Pot, PotState
from src.domain.models.seat import Seat
from src.domain.rules.chip_distributor import ChipDistributor

# =============================================================================
# UNCALLED BET RETURNS (Rule Book Section 12.6)
# =============================================================================


class TestUncalledBetReturnsSingleHighestInvestor:
    """Uncalled bet returned when one player bet more than anyone could match."""

    def test_returns_excess_when_highest_investor_exceeds_second_highest(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Player A(500), C all-in(200), D all-in(350) → return 150 to A."""
        player_a = sample_player_factory(
            player_id="player-a",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(500),
            total_invested_this_hand=ChipAmount(500),
        )
        player_c = sample_player_factory(
            player_id="player-c",
            seat=Seat.SEAT_2,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(200),
        )
        player_d = sample_player_factory(
            player_id="player-d",
            seat=Seat.SEAT_3,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(350),
        )

        result = ChipDistributor.calculate_uncalled_bet_returns(
            [player_a, player_c, player_d]
        )

        assert result == {"player-a": ChipAmount(150)}

    def test_returns_exact_uncalled_amount_two_players(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Two players: A(300), B all-in(100) → return 200 to A."""
        player_a = sample_player_factory(
            player_id="player-a",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(700),
            total_invested_this_hand=ChipAmount(300),
        )
        player_b = sample_player_factory(
            player_id="player-b",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(100),
        )

        result = ChipDistributor.calculate_uncalled_bet_returns(
            [player_a, player_b]
        )

        assert result == {"player-a": ChipAmount(200)}


class TestUncalledBetReturnsNoReturn:
    """No uncalled bet when investments are matched."""

    def test_no_return_when_two_players_share_highest_investment(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """A(500), B(500), C all-in(200) → no return (A and B matched)."""
        player_a = sample_player_factory(
            player_id="player-a",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(500),
            total_invested_this_hand=ChipAmount(500),
        )
        player_b = sample_player_factory(
            player_id="player-b",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(500),
            total_invested_this_hand=ChipAmount(500),
        )
        player_c = sample_player_factory(
            player_id="player-c",
            seat=Seat.SEAT_2,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(200),
        )

        result = ChipDistributor.calculate_uncalled_bet_returns(
            [player_a, player_b, player_c]
        )

        assert result == {}

    def test_no_return_when_all_players_invest_same_amount(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """All equal: A(100), B(100), C(100) → no return."""
        players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(900),
                total_invested_this_hand=ChipAmount(100),
            )
            for i in range(3)
        ]

        result = ChipDistributor.calculate_uncalled_bet_returns(players)

        assert result == {}

    def test_no_return_when_highest_equals_second_highest(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Two players with same investment: A(200), B(200) → no return."""
        player_a = sample_player_factory(
            player_id="player-a",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(800),
            total_invested_this_hand=ChipAmount(200),
        )
        player_b = sample_player_factory(
            player_id="player-b",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(800),
            total_invested_this_hand=ChipAmount(200),
        )

        result = ChipDistributor.calculate_uncalled_bet_returns(
            [player_a, player_b]
        )

        assert result == {}

    def test_no_return_when_three_players_all_share_highest(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Three-way tie at highest: A(300), B(300), C(300) → no return."""
        players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(700),
                total_invested_this_hand=ChipAmount(300),
            )
            for i in range(3)
        ]

        result = ChipDistributor.calculate_uncalled_bet_returns(players)

        assert result == {}


class TestUncalledBetReturnsEdgeCases:
    """Edge cases for uncalled bet calculation."""

    def test_empty_dict_for_single_player(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Single player (won by fold) → no uncalled bet calculation needed."""
        player = sample_player_factory(
            player_id="player-a",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(500),
            total_invested_this_hand=ChipAmount(200),
        )

        result = ChipDistributor.calculate_uncalled_bet_returns([player])

        assert result == {}

    def test_empty_dict_for_empty_list(self) -> None:
        """Empty player list → empty result."""
        result = ChipDistributor.calculate_uncalled_bet_returns([])

        assert result == {}

    def test_handles_zero_investments(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Players with zero investment: A(100), B(0) → return 100 to A."""
        player_a = sample_player_factory(
            player_id="player-a",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(900),
            total_invested_this_hand=ChipAmount(100),
        )
        player_b = sample_player_factory(
            player_id="player-b",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(0),
        )

        result = ChipDistributor.calculate_uncalled_bet_returns(
            [player_a, player_b]
        )

        assert result == {"player-a": ChipAmount(100)}

    def test_large_investment_amounts(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Large amounts: A(100000), B(75000) → return 25000 to A."""
        player_a = sample_player_factory(
            player_id="player-a",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(100000),
        )
        player_b = sample_player_factory(
            player_id="player-b",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(75000),
        )

        result = ChipDistributor.calculate_uncalled_bet_returns(
            [player_a, player_b]
        )

        assert result == {"player-a": ChipAmount(25000)}


# =============================================================================
# POSITION-BASED SORTING (Rule Book Section 12.3)
# =============================================================================


class TestSortWinnersByPositionLeftOfButton:
    """Winners sorted clockwise starting left of button for odd chip distribution."""

    def test_sorts_two_winners_left_of_button_first(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Button at seat 2, winners at seats 0 and 4 → [seat 4, seat 0]."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(6)
        ]
        winners = [all_players[0], all_players[4]]  # Seats 0 and 4
        button_seat = Seat.SEAT_2

        # Clockwise from seat 2: 3 → 4 → 5 → 0 → 1 → 2
        # Winners at 0 and 4: seat 4 comes first, then seat 0
        result = ChipDistributor.sort_winners_by_position_left_of_button(
            winners=winners,
            button_seat=button_seat,
            all_players=all_players,
        )

        assert [p.seat for p in result] == [Seat.SEAT_4, Seat.SEAT_0]

    def test_sorts_three_winners_clockwise_from_button(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Button at seat 2, winners at seats 0, 3, 5 → [seat 3, seat 5, seat 0]."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(6)
        ]
        winners = [all_players[0], all_players[3], all_players[5]]
        button_seat = Seat.SEAT_2

        # Clockwise from seat 2: 3 → 4 → 5 → 0 → 1 → 2
        result = ChipDistributor.sort_winners_by_position_left_of_button(
            winners=winners,
            button_seat=button_seat,
            all_players=all_players,
        )

        assert [p.seat for p in result] == [
            Seat.SEAT_3,
            Seat.SEAT_5,
            Seat.SEAT_0,
        ]

    def test_single_winner_returns_list_with_one_player(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Single winner returns as-is."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(4)
        ]
        winner = all_players[2]

        result = ChipDistributor.sort_winners_by_position_left_of_button(
            winners=[winner],
            button_seat=Seat.SEAT_0,
            all_players=all_players,
        )

        assert result == [winner]

    def test_empty_winners_returns_empty_list(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Empty winners list returns empty list."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(4)
        ]

        result = ChipDistributor.sort_winners_by_position_left_of_button(
            winners=[],
            button_seat=Seat.SEAT_0,
            all_players=all_players,
        )

        assert result == []

    def test_button_at_seat_0_sorts_correctly(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Button at seat 0, winners at seats 1, 3, 5 → [seat 1, seat 3, seat 5]."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(6)
        ]
        winners = [all_players[1], all_players[3], all_players[5]]
        button_seat = Seat.SEAT_0

        # Clockwise from seat 0: 1 → 2 → 3 → 4 → 5 → 0
        result = ChipDistributor.sort_winners_by_position_left_of_button(
            winners=winners,
            button_seat=button_seat,
            all_players=all_players,
        )

        assert [p.seat for p in result] == [
            Seat.SEAT_1,
            Seat.SEAT_3,
            Seat.SEAT_5,
        ]

    def test_button_at_last_seat_wraps_correctly(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Button at seat 5, winners at seats 0, 2, 4 → [seat 0, seat 2, seat 4]."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(6)
        ]
        winners = [all_players[0], all_players[2], all_players[4]]
        button_seat = Seat.SEAT_5

        # Clockwise from seat 5: 0 → 1 → 2 → 3 → 4 → 5
        result = ChipDistributor.sort_winners_by_position_left_of_button(
            winners=winners,
            button_seat=button_seat,
            all_players=all_players,
        )

        assert [p.seat for p in result] == [
            Seat.SEAT_0,
            Seat.SEAT_2,
            Seat.SEAT_4,
        ]

    def test_all_players_are_winners_sorts_all(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """All players win: button at seat 1 → [2, 3, 0, 1]."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(4)
        ]
        button_seat = Seat.SEAT_1

        result = ChipDistributor.sort_winners_by_position_left_of_button(
            winners=all_players,
            button_seat=button_seat,
            all_players=all_players,
        )

        assert [p.seat for p in result] == [
            Seat.SEAT_2,
            Seat.SEAT_3,
            Seat.SEAT_0,
            Seat.SEAT_1,
        ]


# =============================================================================
# SINGLE POT DISTRIBUTION (Rule Book Section 12.2-12.3)
# =============================================================================


class TestDistributePotSingleWinner:
    """Single winner receives entire pot."""

    def test_single_winner_gets_entire_pot(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """One winner: receives full pot amount."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(4)
        ]
        winner = all_players[2]
        pot = Pot(
            amount=ChipAmount(500),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )

        result = ChipDistributor.distribute_pot_to_winners(
            pot=pot,
            winners=[winner],
            button_seat=Seat.SEAT_0,
            all_players=all_players,
        )

        assert result == {"player-2": ChipAmount(500)}

    def test_single_winner_gets_large_pot(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Large pot to single winner."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(2)
        ]
        pot = Pot(
            amount=ChipAmount(100000),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )

        result = ChipDistributor.distribute_pot_to_winners(
            pot=pot,
            winners=[all_players[0]],
            button_seat=Seat.SEAT_1,
            all_players=all_players,
        )

        assert result == {"player-0": ChipAmount(100000)}


class TestDistributePotEvenSplit:
    """Pot splits evenly among multiple winners."""

    def test_two_way_split_even_pot(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """200 chips, 2 winners → 100 each."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(4)
        ]
        winners = [all_players[0], all_players[2]]
        pot = Pot(
            amount=ChipAmount(200),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )

        result = ChipDistributor.distribute_pot_to_winners(
            pot=pot,
            winners=winners,
            button_seat=Seat.SEAT_3,
            all_players=all_players,
        )

        assert result["player-0"] == ChipAmount(100)
        assert result["player-2"] == ChipAmount(100)

    def test_three_way_split_even_pot(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """300 chips, 3 winners → 100 each."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(6)
        ]
        winners = [all_players[1], all_players[3], all_players[5]]
        pot = Pot(
            amount=ChipAmount(300),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )

        result = ChipDistributor.distribute_pot_to_winners(
            pot=pot,
            winners=winners,
            button_seat=Seat.SEAT_0,
            all_players=all_players,
        )

        assert result["player-1"] == ChipAmount(100)
        assert result["player-3"] == ChipAmount(100)
        assert result["player-5"] == ChipAmount(100)

    def test_four_way_split_even_pot(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """400 chips, 4 winners → 100 each."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(4)
        ]
        pot = Pot(
            amount=ChipAmount(400),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )

        result = ChipDistributor.distribute_pot_to_winners(
            pot=pot,
            winners=all_players,
            button_seat=Seat.SEAT_0,
            all_players=all_players,
        )

        for player in all_players:
            assert result[player.id] == ChipAmount(100)


class TestDistributePotOddChips:
    """Odd chips go to players left of button (Rule Book Section 12.3)."""

    def test_two_way_split_odd_chip_goes_left_of_button(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """101 chips, 2 winners, button at seat 0 → seat 1 gets 51, seat 3 gets 50."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(4)
        ]
        winners = [all_players[1], all_players[3]]  # Seats 1 and 3
        pot = Pot(
            amount=ChipAmount(101),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )
        button_seat = Seat.SEAT_0

        # Clockwise from button: 1 → 2 → 3 → 0
        # Winners: seat 1 first, then seat 3
        # Seat 1 gets odd chip
        result = ChipDistributor.distribute_pot_to_winners(
            pot=pot,
            winners=winners,
            button_seat=button_seat,
            all_players=all_players,
        )

        assert result["player-1"] == ChipAmount(51)
        assert result["player-3"] == ChipAmount(50)

    def test_three_way_split_two_odd_chips(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """155 chips, 3 winners → 52, 52, 51 (first two left of button get extra)."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(6)
        ]
        # Winners at seats 0, 3, 5
        winners = [all_players[0], all_players[3], all_players[5]]
        pot = Pot(
            amount=ChipAmount(155),  # 155 / 3 = 51 remainder 2
            eligible_player_ids=frozenset(p.id for p in all_players),
        )
        button_seat = Seat.SEAT_2

        # Clockwise from seat 2: 3 → 4 → 5 → 0 → 1 → 2
        # Winners in order: seat 3 → seat 5 → seat 0
        # Seat 3 and 5 get odd chips (first 2)
        result = ChipDistributor.distribute_pot_to_winners(
            pot=pot,
            winners=winners,
            button_seat=button_seat,
            all_players=all_players,
        )

        assert result["player-3"] == ChipAmount(52)  # First left of button
        assert result["player-5"] == ChipAmount(52)  # Second left of button
        assert result["player-0"] == ChipAmount(51)  # Third

    def test_four_way_split_three_odd_chips(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """103 chips, 4 winners → 26, 26, 26, 25."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(4)
        ]
        pot = Pot(
            amount=ChipAmount(103),  # 103 / 4 = 25 remainder 3
            eligible_player_ids=frozenset(p.id for p in all_players),
        )
        button_seat = Seat.SEAT_0

        # Clockwise from seat 0: 1 → 2 → 3 → 0
        # First 3 get odd chips
        result = ChipDistributor.distribute_pot_to_winners(
            pot=pot,
            winners=all_players,
            button_seat=button_seat,
            all_players=all_players,
        )

        assert result["player-1"] == ChipAmount(26)  # 1st left of button
        assert result["player-2"] == ChipAmount(26)  # 2nd left of button
        assert result["player-3"] == ChipAmount(26)  # 3rd left of button
        assert result["player-0"] == ChipAmount(25)  # 4th (button)

    def test_two_way_split_one_chip_pot(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """1 chip pot, 2 winners → first left of button gets it."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(4)
        ]
        winners = [all_players[1], all_players[3]]
        pot = Pot(
            amount=ChipAmount(1),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )
        button_seat = Seat.SEAT_0

        result = ChipDistributor.distribute_pot_to_winners(
            pot=pot,
            winners=winners,
            button_seat=button_seat,
            all_players=all_players,
        )

        assert result["player-1"] == ChipAmount(1)
        assert result["player-3"] == ChipAmount(0)

    def test_odd_chip_with_button_position_change(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Same winners, different button → different odd chip recipient."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(4)
        ]
        winners = [all_players[0], all_players[2]]
        pot = Pot(
            amount=ChipAmount(101),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )

        # Button at seat 1: clockwise 2 → 3 → 0 → 1
        # Seat 2 gets odd chip
        result_button_1 = ChipDistributor.distribute_pot_to_winners(
            pot=pot,
            winners=winners,
            button_seat=Seat.SEAT_1,
            all_players=all_players,
        )

        # Button at seat 3: clockwise 0 → 1 → 2 → 3
        # Seat 0 gets odd chip
        result_button_3 = ChipDistributor.distribute_pot_to_winners(
            pot=pot,
            winners=winners,
            button_seat=Seat.SEAT_3,
            all_players=all_players,
        )

        assert result_button_1["player-2"] == ChipAmount(51)
        assert result_button_1["player-0"] == ChipAmount(50)

        assert result_button_3["player-0"] == ChipAmount(51)
        assert result_button_3["player-2"] == ChipAmount(50)


class TestDistributePotEdgeCases:
    """Edge cases for single pot distribution."""

    def test_empty_winners_returns_empty_dict(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """No winners → empty result."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(4)
        ]
        pot = Pot(
            amount=ChipAmount(500),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )

        result = ChipDistributor.distribute_pot_to_winners(
            pot=pot,
            winners=[],
            button_seat=Seat.SEAT_0,
            all_players=all_players,
        )

        assert result == {}

    def test_zero_pot_distributes_zero(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Zero pot → winners get zero each."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(2)
        ]
        pot = Pot(
            amount=ChipAmount(0),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )

        result = ChipDistributor.distribute_pot_to_winners(
            pot=pot,
            winners=all_players,
            button_seat=Seat.SEAT_0,
            all_players=all_players,
        )

        assert result["player-0"] == ChipAmount(0)
        assert result["player-1"] == ChipAmount(0)


# =============================================================================
# ALL POTS DISTRIBUTION (Rule Book Section 9.4)
# =============================================================================


class TestDistributeAllPotsSinglePot:
    """Distribution when only main pot exists."""

    def test_distributes_main_pot_only(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Single main pot distributed to winner."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(3)
        ]
        main_pot = Pot(
            amount=ChipAmount(300),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )
        pot_state = PotState(main_pot=main_pot, side_pots=[])
        winners_by_pot = {main_pot: [all_players[1]]}

        result = ChipDistributor.distribute_all_pots(
            pot_state=pot_state,
            winners_by_pot=winners_by_pot,
            button_seat=Seat.SEAT_0,
            all_players=all_players,
        )

        assert result == {"player-1": ChipAmount(300)}


class TestDistributeAllPotsProcessingOrder:
    """Pots processed in order: fewest eligible players first (Section 9.4)."""

    def test_side_pots_processed_before_main_pot(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Side pots (fewer eligible) processed before main pot."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(0),
            )
            for i in range(4)
        ]

        # Main pot: 4 eligible
        main_pot = Pot(
            amount=ChipAmount(400),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )
        # Side pot 1: 3 eligible
        side_pot_1 = Pot(
            amount=ChipAmount(300),
            eligible_player_ids=frozenset(
                p.id for p in all_players[1:]
            ),  # Players 1, 2, 3
        )
        # Side pot 2: 2 eligible (processed first)
        side_pot_2 = Pot(
            amount=ChipAmount(200),
            eligible_player_ids=frozenset(
                [all_players[2].id, all_players[3].id]
            ),
        )

        pot_state = PotState(
            main_pot=main_pot, side_pots=[side_pot_1, side_pot_2]
        )

        # Different winners for each pot
        winners_by_pot = {
            main_pot: [all_players[0]],  # Player 0 wins main
            side_pot_1: [all_players[1]],  # Player 1 wins side pot 1
            side_pot_2: [all_players[2]],  # Player 2 wins side pot 2
        }

        result = ChipDistributor.distribute_all_pots(
            pot_state=pot_state,
            winners_by_pot=winners_by_pot,
            button_seat=Seat.SEAT_0,
            all_players=all_players,
        )

        assert result["player-0"] == ChipAmount(400)  # Main pot
        assert result["player-1"] == ChipAmount(300)  # Side pot 1
        assert result["player-2"] == ChipAmount(200)  # Side pot 2


class TestDistributeAllPotsMultipleWins:
    """Player wins multiple pots - payouts aggregated."""

    def test_same_player_wins_main_and_side_pot(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """One player wins both pots → payouts summed."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(0),
            )
            for i in range(3)
        ]

        main_pot = Pot(
            amount=ChipAmount(300),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )
        side_pot = Pot(
            amount=ChipAmount(200),
            eligible_player_ids=frozenset(
                [all_players[1].id, all_players[2].id]
            ),
        )

        pot_state = PotState(main_pot=main_pot, side_pots=[side_pot])

        # Player 2 wins both pots
        winners_by_pot = {
            main_pot: [all_players[2]],
            side_pot: [all_players[2]],
        }

        result = ChipDistributor.distribute_all_pots(
            pot_state=pot_state,
            winners_by_pot=winners_by_pot,
            button_seat=Seat.SEAT_0,
            all_players=all_players,
        )

        assert result["player-2"] == ChipAmount(500)  # 300 + 200

    def test_same_player_wins_all_three_pots(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Player wins main + 2 side pots."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(0),
            )
            for i in range(4)
        ]

        main_pot = Pot(
            amount=ChipAmount(400),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )
        side_pot_1 = Pot(
            amount=ChipAmount(300),
            eligible_player_ids=frozenset(p.id for p in all_players[1:]),
        )
        side_pot_2 = Pot(
            amount=ChipAmount(200),
            eligible_player_ids=frozenset(
                [all_players[2].id, all_players[3].id]
            ),
        )

        pot_state = PotState(
            main_pot=main_pot, side_pots=[side_pot_1, side_pot_2]
        )

        # Player 3 wins all
        winners_by_pot = {
            main_pot: [all_players[3]],
            side_pot_1: [all_players[3]],
            side_pot_2: [all_players[3]],
        }

        result = ChipDistributor.distribute_all_pots(
            pot_state=pot_state,
            winners_by_pot=winners_by_pot,
            button_seat=Seat.SEAT_0,
            all_players=all_players,
        )

        assert result["player-3"] == ChipAmount(900)  # 400 + 300 + 200


class TestDistributeAllPotsDifferentWinners:
    """Different players win different pots."""

    def test_all_in_player_wins_main_another_wins_side(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """All-in player wins main pot, different player wins side pot."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(0),
            )
            for i in range(3)
        ]

        # Player 0 went all-in first (lowest investment)
        # Main pot: all 3 eligible
        main_pot = Pot(
            amount=ChipAmount(150),  # 50 * 3
            eligible_player_ids=frozenset(p.id for p in all_players),
        )
        # Side pot: only players 1 and 2 eligible
        side_pot = Pot(
            amount=ChipAmount(100),  # 50 * 2 (excess above player 0's all-in)
            eligible_player_ids=frozenset(
                [all_players[1].id, all_players[2].id]
            ),
        )

        pot_state = PotState(main_pot=main_pot, side_pots=[side_pot])

        # Player 0 wins main (best hand among all 3)
        # Player 1 wins side (best hand among 1 and 2)
        winners_by_pot = {
            main_pot: [all_players[0]],
            side_pot: [all_players[1]],
        }

        result = ChipDistributor.distribute_all_pots(
            pot_state=pot_state,
            winners_by_pot=winners_by_pot,
            button_seat=Seat.SEAT_2,
            all_players=all_players,
        )

        assert result["player-0"] == ChipAmount(150)  # Main pot only
        assert result["player-1"] == ChipAmount(100)  # Side pot only
        assert "player-2" not in result  # Won nothing


class TestDistributeAllPotsSplitPots:
    """Split pots with odd chips across multiple pots."""

    def test_split_main_pot_single_winner_side_pot(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Main pot split 2 ways, side pot to single winner."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(0),
            )
            for i in range(3)
        ]

        main_pot = Pot(
            amount=ChipAmount(300),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )
        side_pot = Pot(
            amount=ChipAmount(200),
            eligible_player_ids=frozenset(
                [all_players[1].id, all_players[2].id]
            ),
        )

        pot_state = PotState(main_pot=main_pot, side_pots=[side_pot])

        # Players 0 and 1 tie for main pot
        # Player 2 wins side pot alone
        winners_by_pot = {
            main_pot: [all_players[0], all_players[1]],
            side_pot: [all_players[2]],
        }

        result = ChipDistributor.distribute_all_pots(
            pot_state=pot_state,
            winners_by_pot=winners_by_pot,
            button_seat=Seat.SEAT_0,
            all_players=all_players,
        )

        # Main pot: 300 / 2 = 150 each
        assert result["player-0"] == ChipAmount(150)
        assert result["player-1"] == ChipAmount(150)
        # Side pot: 200 to player 2
        assert result["player-2"] == ChipAmount(200)

    def test_odd_chips_distributed_correctly_in_split_main_pot(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Main pot with odd chip split, side pot clean split."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(0),
            )
            for i in range(4)
        ]

        # 301 chips, 3-way tie → 100, 100, 101 (or similar distribution)
        main_pot = Pot(
            amount=ChipAmount(301),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )
        side_pot = Pot(
            amount=ChipAmount(200),
            eligible_player_ids=frozenset(
                [all_players[1].id, all_players[2].id, all_players[3].id]
            ),
        )

        pot_state = PotState(main_pot=main_pot, side_pots=[side_pot])

        # Main: 3-way tie (players 0, 1, 2)
        # Side: single winner (player 3)
        winners_by_pot = {
            main_pot: [all_players[0], all_players[1], all_players[2]],
            side_pot: [all_players[3]],
        }
        button_seat = Seat.SEAT_0

        result = ChipDistributor.distribute_all_pots(
            pot_state=pot_state,
            winners_by_pot=winners_by_pot,
            button_seat=button_seat,
            all_players=all_players,
        )

        # Main pot: 301 / 3 = 100 remainder 1
        # Order from button 0: 1 → 2 → 3 → 0
        # Winners 0, 1, 2 in order: 1, 2, 0
        # Seat 1 gets odd chip
        total_main = (
            result["player-0"].value
            + result["player-1"].value
            + result["player-2"].value
        )
        assert total_main == 301
        assert result["player-1"] == ChipAmount(101)  # First left of button
        assert result["player-2"] == ChipAmount(100)
        assert result["player-0"] == ChipAmount(100)

        # Side pot to player 3
        assert result["player-3"] == ChipAmount(200)


class TestDistributeAllPotsEdgeCases:
    """Edge cases for all pots distribution."""

    def test_missing_winners_for_pot_skipped(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Pot with no winners in mapping is skipped."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(0),
            )
            for i in range(3)
        ]

        main_pot = Pot(
            amount=ChipAmount(300),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )
        side_pot = Pot(
            amount=ChipAmount(200),
            eligible_player_ids=frozenset(
                [all_players[1].id, all_players[2].id]
            ),
        )

        pot_state = PotState(main_pot=main_pot, side_pots=[side_pot])

        # Only provide winners for main pot (side pot missing)
        winners_by_pot: dict[Pot, list[Player]] = {
            main_pot: [all_players[0]],
        }

        result = ChipDistributor.distribute_all_pots(
            pot_state=pot_state,
            winners_by_pot=winners_by_pot,
            button_seat=Seat.SEAT_0,
            all_players=all_players,
        )

        # Only main pot distributed
        assert result == {"player-0": ChipAmount(300)}

    def test_empty_winners_list_for_pot_skipped(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Pot with empty winners list is skipped."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(0),
            )
            for i in range(3)
        ]

        main_pot = Pot(
            amount=ChipAmount(300),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )
        side_pot = Pot(
            amount=ChipAmount(200),
            eligible_player_ids=frozenset(
                [all_players[1].id, all_players[2].id]
            ),
        )

        pot_state = PotState(main_pot=main_pot, side_pots=[side_pot])

        winners_by_pot: dict[Pot, list[Player]] = {
            main_pot: [all_players[0]],
            side_pot: [],  # Empty winners list
        }

        result = ChipDistributor.distribute_all_pots(
            pot_state=pot_state,
            winners_by_pot=winners_by_pot,
            button_seat=Seat.SEAT_0,
            all_players=all_players,
        )

        assert result == {"player-0": ChipAmount(300)}


# =============================================================================
# ADDITIONAL EDGE CASES AND DEFENSIVE TESTS
# =============================================================================


class TestSortWinnersByPositionAdjacentSeats:
    """Edge cases for position sorting with adjacent and non-contiguous seats."""

    def test_adjacent_winners_sorted_correctly(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Winners at adjacent seats: 1, 2, 3 with button at 0 → [1, 2, 3]."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(6)
        ]
        winners = [all_players[1], all_players[2], all_players[3]]
        button_seat = Seat.SEAT_0

        result = ChipDistributor.sort_winners_by_position_left_of_button(
            winners=winners,
            button_seat=button_seat,
            all_players=all_players,
        )

        assert [p.seat for p in result] == [
            Seat.SEAT_1,
            Seat.SEAT_2,
            Seat.SEAT_3,
        ]

    def test_button_is_winner_sorted_last(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Button player is winner → sorted last (furthest from left of button)."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(4)
        ]
        # Winners include the button (seat 2)
        winners = [all_players[0], all_players[2], all_players[3]]
        button_seat = Seat.SEAT_2

        # Clockwise from seat 2: 3 → 0 → 1 → 2
        # Winners in order: 3 → 0 → 2 (button last)
        result = ChipDistributor.sort_winners_by_position_left_of_button(
            winners=winners,
            button_seat=button_seat,
            all_players=all_players,
        )

        assert [p.seat for p in result] == [
            Seat.SEAT_3,
            Seat.SEAT_0,
            Seat.SEAT_2,
        ]

    def test_winners_wrap_around_table(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Winners span wrap-around: button at 3, winners at 5, 0, 1."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(6)
        ]
        winners = [all_players[5], all_players[0], all_players[1]]
        button_seat = Seat.SEAT_3

        # Clockwise from seat 3: 4 → 5 → 0 → 1 → 2 → 3
        result = ChipDistributor.sort_winners_by_position_left_of_button(
            winners=winners,
            button_seat=button_seat,
            all_players=all_players,
        )

        assert [p.seat for p in result] == [
            Seat.SEAT_5,
            Seat.SEAT_0,
            Seat.SEAT_1,
        ]


class TestDistributePotFiveAndSixWaySplits:
    """Test larger splits (5-6 way) to ensure algorithm scales correctly."""

    def test_five_way_split_even_pot(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """500 chips, 5 winners → 100 each."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(6)
        ]
        winners = all_players[:5]  # First 5 players
        pot = Pot(
            amount=ChipAmount(500),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )

        result = ChipDistributor.distribute_pot_to_winners(
            pot=pot,
            winners=winners,
            button_seat=Seat.SEAT_5,
            all_players=all_players,
        )

        for i in range(5):
            assert result[f"player-{i}"] == ChipAmount(100)

    def test_five_way_split_four_odd_chips(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """504 chips, 5 winners → 101, 101, 101, 101, 100 (max remainder case)."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(6)
        ]
        winners = all_players[:5]
        pot = Pot(
            amount=ChipAmount(504),  # 504 / 5 = 100 remainder 4
            eligible_player_ids=frozenset(p.id for p in all_players),
        )
        button_seat = Seat.SEAT_5

        # Clockwise from seat 5: 0 → 1 → 2 → 3 → 4 → 5
        # First 4 get odd chips
        result = ChipDistributor.distribute_pot_to_winners(
            pot=pot,
            winners=winners,
            button_seat=button_seat,
            all_players=all_players,
        )

        assert result["player-0"] == ChipAmount(101)  # 1st left of button
        assert result["player-1"] == ChipAmount(101)  # 2nd
        assert result["player-2"] == ChipAmount(101)  # 3rd
        assert result["player-3"] == ChipAmount(101)  # 4th
        assert result["player-4"] == ChipAmount(100)  # 5th (no odd chip)

        # Verify total
        total = sum(amt.value for amt in result.values())
        assert total == 504

    def test_six_way_split_five_odd_chips(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """605 chips, 6 winners → 101, 101, 101, 101, 101, 100."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(6)
        ]
        pot = Pot(
            amount=ChipAmount(605),  # 605 / 6 = 100 remainder 5
            eligible_player_ids=frozenset(p.id for p in all_players),
        )
        button_seat = Seat.SEAT_0

        # Clockwise from seat 0: 1 → 2 → 3 → 4 → 5 → 0
        result = ChipDistributor.distribute_pot_to_winners(
            pot=pot,
            winners=all_players,
            button_seat=button_seat,
            all_players=all_players,
        )

        assert result["player-1"] == ChipAmount(101)  # 1st left of button
        assert result["player-2"] == ChipAmount(101)  # 2nd
        assert result["player-3"] == ChipAmount(101)  # 3rd
        assert result["player-4"] == ChipAmount(101)  # 4th
        assert result["player-5"] == ChipAmount(101)  # 5th
        assert result["player-0"] == ChipAmount(
            100
        )  # 6th (button, no odd chip)

        total = sum(amt.value for amt in result.values())
        assert total == 605


class TestDistributePotHeadsUpScenarios:
    """Heads-up (2 player) specific distribution scenarios."""

    def test_heads_up_split_pot_even(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Heads-up tie with even pot → 50/50 split."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(500),
            )
            for i in range(2)
        ]
        pot = Pot(
            amount=ChipAmount(200),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )

        result = ChipDistributor.distribute_pot_to_winners(
            pot=pot,
            winners=all_players,
            button_seat=Seat.SEAT_0,
            all_players=all_players,
        )

        assert result["player-0"] == ChipAmount(100)
        assert result["player-1"] == ChipAmount(100)

    def test_heads_up_split_pot_odd_to_left_of_button(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Heads-up tie with odd pot → player left of button gets extra chip."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(500),
            )
            for i in range(2)
        ]
        pot = Pot(
            amount=ChipAmount(201),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )
        button_seat = Seat.SEAT_0

        # Clockwise from seat 0: seat 1 is first left of button
        result = ChipDistributor.distribute_pot_to_winners(
            pot=pot,
            winners=all_players,
            button_seat=button_seat,
            all_players=all_players,
        )

        assert result["player-1"] == ChipAmount(101)  # Left of button
        assert result["player-0"] == ChipAmount(100)  # Button


class TestSidePotWithTiedWinners:
    """Side pot distribution when multiple players tie for a side pot."""

    def test_side_pot_two_way_tie(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Side pot won by two players who tie."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(0),
            )
            for i in range(3)
        ]

        main_pot = Pot(
            amount=ChipAmount(300),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )
        side_pot = Pot(
            amount=ChipAmount(200),
            eligible_player_ids=frozenset(
                [all_players[1].id, all_players[2].id]
            ),
        )

        pot_state = PotState(main_pot=main_pot, side_pots=[side_pot])

        # Player 0 wins main pot
        # Players 1 and 2 TIE for side pot
        winners_by_pot = {
            main_pot: [all_players[0]],
            side_pot: [all_players[1], all_players[2]],  # Tie!
        }
        button_seat = Seat.SEAT_0

        result = ChipDistributor.distribute_all_pots(
            pot_state=pot_state,
            winners_by_pot=winners_by_pot,
            button_seat=button_seat,
            all_players=all_players,
        )

        assert result["player-0"] == ChipAmount(300)  # Main pot
        # Side pot 200 split 2 ways = 100 each
        assert result["player-1"] == ChipAmount(100)
        assert result["player-2"] == ChipAmount(100)

    def test_side_pot_three_way_tie_with_odd_chip(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Side pot three-way tie with odd chip distribution."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(0),
            )
            for i in range(4)
        ]

        main_pot = Pot(
            amount=ChipAmount(400),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )
        side_pot = Pot(
            amount=ChipAmount(301),  # 301 / 3 = 100 remainder 1
            eligible_player_ids=frozenset(
                [all_players[1].id, all_players[2].id, all_players[3].id]
            ),
        )

        pot_state = PotState(main_pot=main_pot, side_pots=[side_pot])

        # Player 0 wins main pot
        # Players 1, 2, 3 TIE for side pot
        winners_by_pot = {
            main_pot: [all_players[0]],
            side_pot: [all_players[1], all_players[2], all_players[3]],
        }
        button_seat = Seat.SEAT_0

        # Clockwise from seat 0: 1 → 2 → 3 → 0
        # Side pot winners in order: 1 → 2 → 3
        # Player 1 gets odd chip
        result = ChipDistributor.distribute_all_pots(
            pot_state=pot_state,
            winners_by_pot=winners_by_pot,
            button_seat=button_seat,
            all_players=all_players,
        )

        assert result["player-0"] == ChipAmount(400)  # Main pot
        assert result["player-1"] == ChipAmount(101)  # 100 + 1 odd chip
        assert result["player-2"] == ChipAmount(100)
        assert result["player-3"] == ChipAmount(100)


class TestDefensiveChecks:
    """Defensive tests to ensure robust behavior."""

    def test_non_winners_not_in_payout_dict(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Players who didn't win should not appear in payout dictionary."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(4)
        ]
        winners = [all_players[0]]  # Only player 0 wins
        pot = Pot(
            amount=ChipAmount(500),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )

        result = ChipDistributor.distribute_pot_to_winners(
            pot=pot,
            winners=winners,
            button_seat=Seat.SEAT_3,
            all_players=all_players,
        )

        # Only winner should be in result
        assert "player-0" in result
        assert "player-1" not in result
        assert "player-2" not in result
        assert "player-3" not in result

    def test_all_payouts_are_non_negative(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """All payout amounts should be >= 0."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(6)
        ]
        pot = Pot(
            amount=ChipAmount(5),  # Very small pot split 6 ways
            eligible_player_ids=frozenset(p.id for p in all_players),
        )

        result = ChipDistributor.distribute_pot_to_winners(
            pot=pot,
            winners=all_players,
            button_seat=Seat.SEAT_0,
            all_players=all_players,
        )

        for player_id, amount in result.items():
            assert (
                amount.value >= 0
            ), f"Player {player_id} has negative payout: {amount}"

    def test_small_pot_large_split_some_get_zero(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """When pot is smaller than number of winners, some get zero."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(6)
        ]
        pot = Pot(
            amount=ChipAmount(3),  # 3 chips split 6 ways
            eligible_player_ids=frozenset(p.id for p in all_players),
        )
        button_seat = Seat.SEAT_0

        # Clockwise from seat 0: 1 → 2 → 3 → 4 → 5 → 0
        result = ChipDistributor.distribute_pot_to_winners(
            pot=pot,
            winners=all_players,
            button_seat=button_seat,
            all_players=all_players,
        )

        # 3 / 6 = 0 remainder 3
        # First 3 left of button get 1 chip each
        assert result["player-1"] == ChipAmount(1)
        assert result["player-2"] == ChipAmount(1)
        assert result["player-3"] == ChipAmount(1)
        assert result["player-4"] == ChipAmount(0)
        assert result["player-5"] == ChipAmount(0)
        assert result["player-0"] == ChipAmount(0)

        # Total still preserved
        total = sum(amt.value for amt in result.values())
        assert total == 3


class TestUncalledBetReturnsAdditionalScenarios:
    """Additional uncalled bet return scenarios."""

    def test_four_players_with_different_investments(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """A(1000), B(500), C(300), D(100) → return 500 to A."""
        players = [
            sample_player_factory(
                player_id="player-a",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(0),
                total_invested_this_hand=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="player-b",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(0),
                total_invested_this_hand=ChipAmount(500),
            ),
            sample_player_factory(
                player_id="player-c",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(0),
                total_invested_this_hand=ChipAmount(300),
            ),
            sample_player_factory(
                player_id="player-d",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(0),
                total_invested_this_hand=ChipAmount(100),
            ),
        ]

        result = ChipDistributor.calculate_uncalled_bet_returns(players)

        # Highest: 1000 (A), Second highest: 500 (B)
        # Uncalled: 1000 - 500 = 500
        assert result == {"player-a": ChipAmount(500)}

    def test_all_players_all_in_at_different_levels(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """All all-in: A(100), B(200), C(300) → return 100 to C."""
        players = [
            sample_player_factory(
                player_id="player-a",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(0),  # All-in
                total_invested_this_hand=ChipAmount(100),
            ),
            sample_player_factory(
                player_id="player-b",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(0),  # All-in
                total_invested_this_hand=ChipAmount(200),
            ),
            sample_player_factory(
                player_id="player-c",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(0),  # All-in
                total_invested_this_hand=ChipAmount(300),
            ),
        ]

        result = ChipDistributor.calculate_uncalled_bet_returns(players)

        # Highest: 300 (C), Second highest: 200 (B)
        # Uncalled: 300 - 200 = 100
        assert result == {"player-c": ChipAmount(100)}


# =============================================================================
# CHIP ACCOUNTING CORRECTNESS
# =============================================================================


class TestChipAccountingTotalPreservation:
    """Total chips distributed equals total pot amount."""

    def test_total_distributed_equals_pot_amount_single_winner(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Single winner: total distributed = pot amount."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(4)
        ]
        pot = Pot(
            amount=ChipAmount(1234),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )

        result = ChipDistributor.distribute_pot_to_winners(
            pot=pot,
            winners=[all_players[2]],
            button_seat=Seat.SEAT_0,
            all_players=all_players,
        )

        total_distributed = sum(amt.value for amt in result.values())
        assert total_distributed == 1234

    def test_total_distributed_equals_pot_amount_even_split(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Even split: total distributed = pot amount."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(4)
        ]
        pot = Pot(
            amount=ChipAmount(400),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )

        result = ChipDistributor.distribute_pot_to_winners(
            pot=pot,
            winners=all_players,
            button_seat=Seat.SEAT_0,
            all_players=all_players,
        )

        total_distributed = sum(amt.value for amt in result.values())
        assert total_distributed == 400

    def test_total_distributed_equals_pot_amount_odd_split(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Odd split: total distributed still equals pot amount."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(1000),
            )
            for i in range(4)
        ]
        pot = Pot(
            amount=ChipAmount(103),  # 103 / 4 = 25 r 3
            eligible_player_ids=frozenset(p.id for p in all_players),
        )

        result = ChipDistributor.distribute_pot_to_winners(
            pot=pot,
            winners=all_players,
            button_seat=Seat.SEAT_0,
            all_players=all_players,
        )

        total_distributed = sum(amt.value for amt in result.values())
        assert total_distributed == 103

    def test_total_all_pots_equals_sum_of_all_pot_amounts(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """All pots distribution: total equals sum of all pots."""
        all_players = [
            sample_player_factory(
                player_id=f"player-{i}",
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(0),
            )
            for i in range(4)
        ]

        main_pot = Pot(
            amount=ChipAmount(400),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )
        side_pot_1 = Pot(
            amount=ChipAmount(301),  # Odd amount
            eligible_player_ids=frozenset(p.id for p in all_players[1:]),
        )
        side_pot_2 = Pot(
            amount=ChipAmount(202),  # Odd amount
            eligible_player_ids=frozenset(
                [all_players[2].id, all_players[3].id]
            ),
        )

        pot_state = PotState(
            main_pot=main_pot, side_pots=[side_pot_1, side_pot_2]
        )

        winners_by_pot = {
            main_pot: [all_players[0], all_players[1]],  # Split main
            side_pot_1: [
                all_players[1],
                all_players[2],
                all_players[3],
            ],  # 3-way split
            side_pot_2: [all_players[3]],  # Single winner
        }

        result = ChipDistributor.distribute_all_pots(
            pot_state=pot_state,
            winners_by_pot=winners_by_pot,
            button_seat=Seat.SEAT_0,
            all_players=all_players,
        )

        total_distributed = sum(amt.value for amt in result.values())
        total_pots = 400 + 301 + 202
        assert total_distributed == total_pots


class TestChipAccountingComplexScenario:
    """Complex realistic scenarios verifying correct chip distribution."""

    def test_rule_book_example_four_players_multiple_all_ins(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Rule Book example: A(100), B(300), C(500), D(500).

        Main pot: 400 (4 eligible)
        Side pot 1: 600 (3 eligible: B, C, D)
        Side pot 2: 400 (2 eligible: C, D)
        Total: 1400
        """
        all_players = [
            sample_player_factory(
                player_id="player-a",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(0),
                total_invested_this_hand=ChipAmount(100),
            ),
            sample_player_factory(
                player_id="player-b",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(0),
                total_invested_this_hand=ChipAmount(300),
            ),
            sample_player_factory(
                player_id="player-c",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(0),
                total_invested_this_hand=ChipAmount(500),
            ),
            sample_player_factory(
                player_id="player-d",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(0),
                total_invested_this_hand=ChipAmount(500),
            ),
        ]

        main_pot = Pot(
            amount=ChipAmount(400),  # 100 * 4
            eligible_player_ids=frozenset(p.id for p in all_players),
        )
        side_pot_1 = Pot(
            amount=ChipAmount(600),  # 200 * 3
            eligible_player_ids=frozenset(
                ["player-b", "player-c", "player-d"]
            ),
        )
        side_pot_2 = Pot(
            amount=ChipAmount(400),  # 200 * 2
            eligible_player_ids=frozenset(["player-c", "player-d"]),
        )

        pot_state = PotState(
            main_pot=main_pot, side_pots=[side_pot_1, side_pot_2]
        )

        # Scenario: Player A (short stack) wins main pot with best hand
        # Player C wins both side pots
        winners_by_pot = {
            main_pot: [all_players[0]],  # Player A
            side_pot_1: [all_players[2]],  # Player C
            side_pot_2: [all_players[2]],  # Player C
        }

        result = ChipDistributor.distribute_all_pots(
            pot_state=pot_state,
            winners_by_pot=winners_by_pot,
            button_seat=Seat.SEAT_0,
            all_players=all_players,
        )

        assert result["player-a"] == ChipAmount(400)  # Main pot
        assert result["player-c"] == ChipAmount(1000)  # 600 + 400

        # Verify total
        total_distributed = sum(amt.value for amt in result.values())
        assert total_distributed == 1400

    def test_heads_up_all_in_with_uncalled_bet(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Heads-up: A(1000), B all-in(300) → A gets 700 back, pot is 600."""
        player_a = sample_player_factory(
            player_id="player-a",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(1000),
        )
        player_b = sample_player_factory(
            player_id="player-b",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(300),
        )

        # First, calculate uncalled bet return
        uncalled_returns = ChipDistributor.calculate_uncalled_bet_returns(
            [player_a, player_b]
        )
        assert uncalled_returns == {"player-a": ChipAmount(700)}

        # After returning uncalled bet, pot would be:
        # A: 300, B: 300 → Main pot: 600
        main_pot = Pot(
            amount=ChipAmount(600),
            eligible_player_ids=frozenset(["player-a", "player-b"]),
        )
        pot_state = PotState(main_pot=main_pot, side_pots=[])

        # B wins with better hand
        winners_by_pot = {main_pot: [player_b]}

        result = ChipDistributor.distribute_all_pots(
            pot_state=pot_state,
            winners_by_pot=winners_by_pot,
            button_seat=Seat.SEAT_0,
            all_players=[player_a, player_b],
        )

        assert result == {"player-b": ChipAmount(600)}

        # Total accounting: A invested 1000, gets 700 back, loses 300 to pot
        # B invested 300, wins 600 (profit 300)
        # Net: A loses 300, B gains 300 ✓

    def test_three_way_all_in_with_split_pot(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Three all-ins at different levels with split pot at main."""
        all_players = [
            sample_player_factory(
                player_id="player-a",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(0),
                total_invested_this_hand=ChipAmount(100),
            ),
            sample_player_factory(
                player_id="player-b",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(0),
                total_invested_this_hand=ChipAmount(200),
            ),
            sample_player_factory(
                player_id="player-c",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(0),
                total_invested_this_hand=ChipAmount(200),
            ),
        ]

        # No uncalled bet (B and C both at 200)
        uncalled_returns = ChipDistributor.calculate_uncalled_bet_returns(
            all_players
        )
        assert uncalled_returns == {}

        # Main pot: 300 (100 * 3)
        # Side pot: 200 (100 * 2, from B and C)
        main_pot = Pot(
            amount=ChipAmount(300),
            eligible_player_ids=frozenset(p.id for p in all_players),
        )
        side_pot = Pot(
            amount=ChipAmount(200),
            eligible_player_ids=frozenset(["player-b", "player-c"]),
        )

        pot_state = PotState(main_pot=main_pot, side_pots=[side_pot])

        # A and B tie for main pot, C wins side pot
        winners_by_pot = {
            main_pot: [all_players[0], all_players[1]],  # A and B split
            side_pot: [all_players[2]],  # C wins
        }
        button_seat = Seat.SEAT_0

        result = ChipDistributor.distribute_all_pots(
            pot_state=pot_state,
            winners_by_pot=winners_by_pot,
            button_seat=button_seat,
            all_players=all_players,
        )

        # Main pot split: 300 / 2 = 150 each
        assert result["player-a"] == ChipAmount(150)
        assert result["player-b"] == ChipAmount(150)
        # Side pot to C
        assert result["player-c"] == ChipAmount(200)

        # Total = 500
        total = sum(amt.value for amt in result.values())
        assert total == 500
