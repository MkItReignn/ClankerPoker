from __future__ import annotations

from src.domain.models.chips import ChipAmount
from src.domain.models.player import Player


class BettingCalculator:
    """Calculates betting-related amounts and requirements."""

    @staticmethod
    def calculate_minimum_raise_increment(
        last_raise_increment: ChipAmount, big_blind: ChipAmount
    ) -> ChipAmount:
        """
        Calculate minimum raise increment based on game state.

        Rules:
        - First raise: minimum = big_blind
        - Re-raise: minimum = last_raise_increment (must match or exceed previous raise)
        - Always at least big_blind
        """
        if last_raise_increment.value == 0:
            return big_blind
        return ChipAmount(max(last_raise_increment.value, big_blind.value))

    @staticmethod
    def calculate_call_amount(
        max_invested_this_hand: ChipAmount,
        player_invested_this_hand: ChipAmount,
    ) -> ChipAmount:
        """
        Calculate how much player needs to call to stay in hand.

        Call amount = max_invested_this_hand - player_invested_this_hand

        Returns the full amount needed, regardless of player's available chips.
        The caller is responsible for checking if player has enough chips.
        """
        if player_invested_this_hand >= max_invested_this_hand:
            return ChipAmount(0)

        call_amount: ChipAmount = max_invested_this_hand - player_invested_this_hand
        return call_amount

    @staticmethod
    def get_max_invested_this_hand(players_in_hand: list[Player]) -> ChipAmount:
        """
        Get the maximum amount invested by any player in this hand.
        All other players must match this to stay in the hand.
        """
        if not players_in_hand:
            return ChipAmount(0)

        max_invested = max(p.total_invested_this_hand.value for p in players_in_hand)
        return ChipAmount(max_invested)
