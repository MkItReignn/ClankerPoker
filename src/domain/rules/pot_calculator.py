from __future__ import annotations

from src.domain.models.chips import ChipAmount
from src.domain.models.player import HandParticipationStatus, Player, PlayerId
from src.domain.models.pot import Pot, PotState


class PotCalculator:
    """Calculates pots and side pots."""

    @staticmethod
    def calculate_pot_state(all_players_that_invested: list[Player]) -> PotState:
        """
        Calculate main pot and side pots based on player investments.

        Args:
            all_players_that_invested: ALL players who invested chips (including folded players).
                        Their chips contribute to pot size, but only IN_HAND
                        players are eligible to win.

        Follows standard tournament poker side pot rules:
        1. Sort players by total_invested_this_hand (ascending)
        2. For each unique investment level:
           - Calculate pot size from ALL contributors: (level - previous_level) × contributors
           - Eligible players: only IN_HAND players who invested >= this level
        3. First pot = main pot, rest = side pots

        Returns:
            PotState: Complete pot state containing main pot and any side pots.

        Raises:
            ValueError: If no players provided (invalid game state)
        """
        if not all_players_that_invested:
            raise ValueError(
                "Cannot calculate pot state: no players provided. "
                + "This indicates an invalid game state."
            )

        # Get investments from ALL players (including folded)
        investments: list[tuple[PlayerId, int]] = [
            (player.id, player.total_invested_this_hand.value)
            for player in all_players_that_invested
        ]

        # Get set of IN_HAND players (for eligibility filtering)
        in_hand_player_ids: set[PlayerId] = {
            p.id
            for p in all_players_that_invested
            if p.participation_status == HandParticipationStatus.IN_HAND
        }

        investments.sort(key=lambda x: x[1])

        pots: list[Pot] = []
        previous_level = 0

        # Sort levels in ascending order so main pot (lowest level) is first
        unique_levels: list[int] = sorted(set(investment for _, investment in investments))

        for level in unique_levels:
            # Contributors: all players who invested >= level (for pot size calculation)
            contributors_at_level: set[PlayerId] = {
                player_id for player_id, investment in investments if investment >= level
            }

            # Eligible: only IN_HAND players who invested >= level (for winning)
            eligible_player_ids: set[PlayerId] = {
                player_id for player_id in contributors_at_level if player_id in in_hand_player_ids
            }

            chips_per_player: int = level - previous_level
            # Pot size based on ALL contributors (including folded)
            pot_size: ChipAmount = ChipAmount(chips_per_player * len(contributors_at_level))

            pots.append(
                Pot(
                    amount=pot_size,
                    eligible_player_ids=frozenset(eligible_player_ids),  # Only IN_HAND
                )
            )

            previous_level: int = level

        # Main pot is always the first pot (lowest investment level)
        # It should contain all non-folded players who invested at least the minimum amount
        main_pot: Pot = pots[0]
        side_pots: list[Pot] = pots[1:] if len(pots) > 1 else []

        # Verify main pot contains all non-folded players (invariant check)
        if in_hand_player_ids and not in_hand_player_ids.issubset(main_pot.eligible_player_ids):
            raise ValueError(
                f"Invalid pot calculation: main pot does not contain all non-folded players. "
                f"Non-folded players: {in_hand_player_ids}, "
                f"Main pot eligible: {main_pot.eligible_player_ids}"
            )

        return PotState(main_pot=main_pot, side_pots=side_pots)
