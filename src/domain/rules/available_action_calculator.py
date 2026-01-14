from __future__ import annotations

from src.domain.models.available_action import (
    AvailableActions,
    AvailableAllInAction,
    AvailableCallAction,
    AvailableCheckAction,
    AvailableFoldAction,
    AvailableRaiseAction,
)
from src.domain.models.chips import ChipAmount
from src.domain.models.game import Game
from src.domain.models.player import Player
from src.domain.rules.betting_calculator import BettingCalculator


class AvailableActionCalculator:
    """Calculates available actions for a player given game state.

    Validation is enforced at creation time - only valid actions are returned.
    This eliminates the need for separate action validation.
    """

    @staticmethod
    def calculate_available_actions(game: Game, player: Player) -> list[AvailableActions]:
        """
        Calculate all available actions for a player given current game state.

        Only returns actions that are valid for the current state.
        If player cannot act, returns empty list.

        Returns:
            List of available actions (may be empty if player cannot act).
        """
        players_in_hand = game.players_in_hand(excluded_player_id=player.id)
        if not player.can_act() or len(players_in_hand) == 0:
            return []

        all_players_in_hand = game.players_in_hand()
        max_invested: ChipAmount = BettingCalculator.get_max_invested_this_hand(all_players_in_hand)
        call_amount: ChipAmount = BettingCalculator.calculate_call_amount(
            max_invested, player.total_invested_this_hand
        )

        available_actions: list[AvailableActions] = []

        available_actions.append(AvailableFoldAction())

        if call_amount.value == 0:
            available_actions.append(AvailableCheckAction())

        if call_amount.value > 0:
            if player.remaining_chips.value >= call_amount.value:
                available_actions.append(AvailableCallAction(call_amount=call_amount))

        minimum_raise_increment: ChipAmount = BettingCalculator.calculate_minimum_raise_increment(
            game.betting_state.last_raise_increment,
            game.current_blind_level.big_blind,
        )

        if player.remaining_chips > call_amount:
            max_raise_increment: ChipAmount = player.remaining_chips - call_amount

            if max_raise_increment >= minimum_raise_increment:
                min_raise_amount: ChipAmount = minimum_raise_increment
                max_raise_amount: ChipAmount = max_raise_increment
                available_actions.append(
                    AvailableRaiseAction(
                        min_raise_amount=min_raise_amount, max_raise_amount=max_raise_amount
                    )
                )

        if player.remaining_chips.value > 0:
            available_actions.append(AvailableAllInAction(all_in_amount=player.remaining_chips))

        return available_actions
