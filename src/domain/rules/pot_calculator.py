from __future__ import annotations

from src.domain.models.chips import ChipAmount
from src.domain.models.player import Player
from src.domain.models.pot import Pot, PotState


class PotCalculator:
    """Calculates pots and side pots."""

    @staticmethod
    def calculate_pot_state(players_in_hand: list[Player]) -> PotState:
        """
        Calculate main pot and side pots based on player investments.

        Follows standard tournament poker side pot rules:
        1. Sort players by total_invested_this_hand (ascending)
        2. For each unique investment level:
           - Calculate pot size: (level - previous_level) × eligible_players
           - Eligible players: those who invested >= this level
        3. First pot = main pot, rest = side pots

        Returns:
            PotState: Complete pot state containing main pot and any side pots.

        Raises:
            ValueError: If no players in hand (invalid game state)
        """
        if not players_in_hand:
            raise ValueError(
                "Cannot calculate pot state: no players in hand. "
                + "This indicates an invalid game state - hands should only be evaluated "
                + "when at least one player remains active."
            )

        investments = [
            (player.id, player.total_invested_this_hand.value) for player in players_in_hand
        ]

        investments.sort(key=lambda x: x[1])

        pots: list[Pot] = []
        previous_level = 0

        unique_levels: list[int] = sorted(set(investment for _, investment in investments))

        for level in unique_levels:
            eligible_player_ids = {
                player_id for player_id, investment in investments if investment >= level
            }

            chips_per_player = level - previous_level
            pot_size = ChipAmount(chips_per_player * len(eligible_player_ids))

            pots.append(
                Pot(
                    amount=pot_size,
                    eligible_player_ids=frozenset(eligible_player_ids),
                )
            )

            previous_level = level

        main_pot = pots[0]
        side_pots = pots[1:] if len(pots) > 1 else []

        return PotState(main_pot=main_pot, side_pots=side_pots)
