from __future__ import annotations

from src.domain.models.available_action import (AvailableActions,
                                                AvailableAllInAction,
                                                AvailableBetAction,
                                                AvailableCallAction,
                                                AvailableCheckAction,
                                                AvailableFoldAction,
                                                AvailableRaiseAction)
from src.domain.models.chips import ChipAmount
from src.domain.models.game import Game, GamePhase
from src.domain.models.player import PlayerId
from src.domain.rules.betting_calculator import BettingCalculator


class AvailableActionCalculator:
    """Calculates available actions for a player given game state.

    Validation is enforced at creation time - only valid actions are returned.
    This eliminates the need for separate action validation.
    """

    @staticmethod
    def calculate_available_actions(game: Game, player_id: PlayerId) -> list[AvailableActions]:
        """
        Calculate all available actions for a player given current game state.

        Only returns actions that are valid for the current state.
        If player cannot act, returns empty list.

        Args:
            game: Current game state
            player_id: ID of the player to calculate actions for

        Returns:
            List of available actions (may be empty if player cannot act).
        """
        player = game.players.get_by_id(player_id)
        if player is None:
            raise ValueError(f"Player {player_id} not found in game")

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

            is_post_flop = game.current_phase in (
                GamePhase.FLOP,
                GamePhase.TURN,
                GamePhase.RIVER,
            )
            is_pre_flop = game.current_phase == GamePhase.PRE_FLOP

            # Bet/raise only available if player.can_raise is True (WSOP Rule 96)
            if (
                player.can_raise
                and is_post_flop
                and player.remaining_chips >= game.current_blind_level.big_blind
            ):
                available_actions.append(
                    AvailableBetAction(
                        min_bet_amount=game.current_blind_level.big_blind,
                        max_bet_amount=player.remaining_chips,
                    )
                )

            # You can only raise when call_amount = 0 during pre-flop, since BET is not allowed.
            if player.can_raise and is_pre_flop:
                minimum_raise_increment: ChipAmount = (
                    BettingCalculator.calculate_minimum_raise_increment(
                        game.betting_state.last_raise_increment,
                        game.current_blind_level.big_blind,
                    )
                )

                if player.remaining_chips >= minimum_raise_increment:
                    available_actions.append(
                        AvailableRaiseAction(
                            min_raise_amount=minimum_raise_increment,
                            max_raise_amount=player.remaining_chips,
                        )
                    )

        if call_amount.value > 0:
            if player.remaining_chips.value >= call_amount.value:
                available_actions.append(AvailableCallAction(call_amount=call_amount))

            # Raise only available if player.can_raise is True (WSOP Rule 96)
            if player.can_raise and player.remaining_chips > call_amount:
                min_raise_amount: ChipAmount = BettingCalculator.calculate_minimum_raise_increment(
                    game.betting_state.last_raise_increment,
                    game.current_blind_level.big_blind,
                )
                max_raise_amount: ChipAmount = player.remaining_chips - call_amount

                if max_raise_amount >= min_raise_amount:
                    available_actions.append(
                        AvailableRaiseAction(
                            min_raise_amount=min_raise_amount, max_raise_amount=max_raise_amount
                        )
                    )

        if player.remaining_chips.value > 0:
            available_actions.append(AvailableAllInAction(all_in_amount=player.remaining_chips))

        return available_actions
