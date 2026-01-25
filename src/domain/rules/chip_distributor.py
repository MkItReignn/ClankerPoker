"""Chip distribution logic for poker hands.

This module handles all chip distribution when a hand finishes:
- Uncalled bet returns (before pot calculation)
- Pot distribution to winners (with split pot handling)
- Odd chip distribution (position-based, left of button first)

Follows Texas Hold'em No-Limit Tournament Rules (RULE_BOOK.md):
- Section 9.4: Side Pot Awarding (fewest eligible players first)
- Section 12.2-12.3: Split Pots and Odd Chip Rule
- Section 12.6: Uncalled Bet Returns
"""

from collections import defaultdict

from src.domain.models.chips import ChipAmount
from src.domain.models.player import Player, PlayerId
from src.domain.models.pot import Pot, PotState
from src.domain.models.seat import Seat


class ChipDistributor:
    """Handles all chip distribution logic for poker hands.

    Responsibilities:
    - Distribute pot winnings to winners
    - Handle split pots with odd chip distribution (position-based)
    - Return uncalled bets to bettors
    - Calculate final chip allocations

    Note: This class uses static methods as it has no state.
    All required context is passed as parameters.
    """

    @staticmethod
    def calculate_uncalled_bet_returns(
        players_in_hand: list[Player],
    ) -> dict[PlayerId, ChipAmount]:
        """Calculate uncalled bet returns before pot calculation.

        An uncalled bet occurs when the highest investor put in more chips
        than anyone else could match (because all other players are all-in
        for less or folded). Per Rule Book Section 12.6, only the portion
        that cannot be matched by any player is returned.

        Args:
            players_in_hand: All players still in hand (not folded).

        Returns:
            Mapping of player_id -> amount to return (usually 0 or 1 entry).

        Examples:
            # A(500), B folded, C all-in(200), D all-in(350)
            # Highest: 500, Second-highest: 350
            # Return 150 to A

            # A(500), B(500), C all-in(200)
            # Highest: 500 (tied by A and B)
            # No return - they matched each other
        """
        if len(players_in_hand) < 2:
            return {}

        # Sort by total invested, descending
        sorted_players = sorted(
            players_in_hand,
            key=lambda p: p.total_invested_this_hand.value,
            reverse=True,
        )

        highest_investment = sorted_players[0].total_invested_this_hand
        second_highest_investment = sorted_players[1].total_invested_this_hand

        # If highest equals second highest, bet was fully matched
        if highest_investment <= second_highest_investment:
            return {}

        # Find all players with highest investment
        highest_investors = [
            p
            for p in players_in_hand
            if p.total_invested_this_hand == highest_investment
        ]

        # If multiple players share highest investment, no uncalled bet
        # (they matched each other)
        if len(highest_investors) > 1:
            return {}

        # Single highest investor - return the uncalled portion
        uncalled_amount = ChipAmount(
            highest_investment.value - second_highest_investment.value
        )
        return {highest_investors[0].id: uncalled_amount}

    @staticmethod
    def sort_winners_by_position_left_of_button(
        winners: list[Player],
        button_seat: Seat,
        all_players: list[Player],
    ) -> list[Player]:
        """Sort winners by position relative to button.

        Per Rule Book Section 12.3, odd chips go to "first player left of
        the button" among tied winners. This is always clockwise order
        starting from the seat immediately left of the button (post-flop
        betting order: SB -> BB -> ... -> BTN).

        Args:
            winners: List of winning players.
            button_seat: Current button seat.
            all_players: All players at table (to determine clockwise order).

        Returns:
            Winners sorted by position (left of button first).

        Example:
            Button at Seat 2, Winners at Seats 0, 3, 5
            Clockwise from button: 3 -> 4 -> 5 -> 0 -> 1 -> 2
            Result: [Seat 3 player, Seat 5 player, Seat 0 player]
        """
        if len(winners) <= 1:
            return list(winners)

        # Create seat -> player mapping for winners
        winner_by_seat: dict[Seat, Player] = {p.seat: p for p in winners}

        # Get total number of seats
        total_seats = len(all_players)

        # Build order starting from seat left of button, going clockwise
        ordered_winners: list[Player] = []
        button_index = button_seat.value

        for i in range(1, total_seats + 1):
            seat_index = (button_index + i) % total_seats
            seat = Seat.from_int(seat_index)
            if seat in winner_by_seat:
                ordered_winners.append(winner_by_seat[seat])

        return ordered_winners

    @staticmethod
    def distribute_pot_to_winners(
        pot: Pot,
        winners: list[Player],
        button_seat: Seat,
        all_players: list[Player],
    ) -> dict[PlayerId, ChipAmount]:
        """Distribute a single pot among winners.

        Per Rule Book Section 12.2-12.3:
        - Single winner: entire pot
        - Multiple winners: equal split
        - Odd chips: go to players left of button (clockwise)

        Args:
            pot: The pot to distribute.
            winners: Players who won this pot.
            button_seat: Current button seat.
            all_players: All players at table.

        Returns:
            Mapping of player_id -> payout from this pot.

        Example:
            Pot: 155 chips, 3-way tie
            155 / 3 = 51 remainder 2
            Players left of button get 52, 52, 51
        """
        if not winners:
            return {}

        if len(winners) == 1:
            return {winners[0].id: pot.amount}

        sorted_winners = (
            ChipDistributor.sort_winners_by_position_left_of_button(
                winners=winners,
                button_seat=button_seat,
                all_players=all_players,
            )
        )

        num_winners = len(sorted_winners)
        pot_value = pot.amount.value
        base_payout = pot_value // num_winners
        remainder = pot_value % num_winners

        payouts: dict[PlayerId, ChipAmount] = {}
        for i, player in enumerate(sorted_winners):
            payout = base_payout
            if i < remainder:
                payout += (
                    1  # Odd chip goes to players closest to button's left
                )
            payouts[player.id] = ChipAmount(payout)

        return payouts

    @staticmethod
    def distribute_all_pots(
        pot_state: PotState,
        winners_by_pot: dict[Pot, list[Player]],
        button_seat: Seat,
        all_players: list[Player],
    ) -> dict[PlayerId, ChipAmount]:
        """Distribute all pots (main + side pots) to winners.

        Per Rule Book Section 9.4 and 12.4, pots are awarded starting with
        the "last side pot created (smallest eligible group)" - i.e., fewest
        eligible players first, then working toward the main pot.

        Args:
            pot_state: Complete pot state from PotCalculator.
            winners_by_pot: Mapping of each pot to its winners.
            button_seat: Current button seat.
            all_players: All players at table.

        Returns:
            Aggregated payouts for all players across all pots.

        Example:
            Main pot (4 eligible): 400 chips
            Side pot 1 (3 eligible): 600 chips
            Side pot 2 (2 eligible): 400 chips

            Processing order: Side pot 2 -> Side pot 1 -> Main pot
        """
        total_payouts: dict[PlayerId, ChipAmount] = defaultdict(
            lambda: ChipAmount(0)
        )

        # Collect all pots with their eligibility count
        all_pots: list[tuple[Pot, int]] = []

        # Add main pot
        all_pots.append(
            (pot_state.main_pot, len(pot_state.main_pot.eligible_player_ids))
        )

        # Add side pots
        for side_pot in pot_state.side_pots:
            all_pots.append((side_pot, len(side_pot.eligible_player_ids)))

        # Sort by eligibility count ASCENDING (fewest eligible players first)
        # This ensures side pots are processed before main pot
        all_pots.sort(key=lambda x: x[1])

        # Process each pot in order
        for pot, _ in all_pots:
            winners: list[Player] = winners_by_pot.get(pot, [])
            if not winners:
                # Shouldn't happen in valid game state, but defensive
                continue

            payouts: dict[PlayerId, ChipAmount] = (
                ChipDistributor.distribute_pot_to_winners(
                    pot=pot,
                    winners=winners,
                    button_seat=button_seat,
                    all_players=all_players,
                )
            )

            # Aggregate payouts
            for player_id, amount in payouts.items():
                total_payouts[player_id] += amount

        return dict(total_payouts)
