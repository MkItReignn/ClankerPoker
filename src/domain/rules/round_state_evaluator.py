from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain.models.chips import ChipAmount
from src.domain.models.hand_phase import HandPhase
from src.domain.models.player import Player
from src.domain.rules.betting_calculator import BettingCalculator

if TYPE_CHECKING:
    from src.domain.models.game import Game


class RoundStateEvaluator:
    @staticmethod
    def is_hand_complete(game: Game) -> bool:
        """
        Check if hand is complete.

        A hand is complete when:
        1. We've reached showdown phase
        2. Only one player remains (all others folded)
        """
        if game.current_phase == HandPhase.SHOWDOWN:
            return True

        return len(game.players_in_hand()) == 1

    @staticmethod
    def is_round_complete(game: Game) -> bool:
        """
        Determine if current betting round is complete.

        Framework:
        1. SHOWDOWN has no betting → always complete
        2. If only 1 player remains (not folded) → hand ends → round complete
        3. If only 1 player can act (others all-in) and doesn't owe → round complete
        4. If all players in hand have acted AND investments are equal → round complete
        5. If all players in hand are all-in → round complete (no more betting)
        6. Otherwise → round continues
        """
        if game.current_phase == HandPhase.SHOWDOWN:
            return True

        players_in_hand: list[Player] = game.players_in_hand()

        if len(players_in_hand) == 1:
            return True

        if RoundStateEvaluator._is_only_one_player_able_to_act_with_no_bet_owed(
            players_in_hand
        ):
            return True

        max_invested: ChipAmount = BettingCalculator.get_max_invested_this_hand(
            players_in_hand
        )
        for player in players_in_hand:
            if player.is_all_in():
                continue

            call_amount: ChipAmount = BettingCalculator.calculate_call_amount(
                max_invested, player.total_invested_this_hand
            )
            if call_amount.value > 0:
                return False

            if not player.has_acted_this_round():
                return False

        return True

    @staticmethod
    def _is_only_one_player_able_to_act_with_no_bet_owed(
        players_in_hand: list[Player],
    ) -> bool:
        """Check if only one player can act and they don't owe any chips.

        When only one player is not all-in and they've already matched the highest
        bet, no meaningful betting can occur - they have no one to bet against.
        """
        players_who_can_act = [p for p in players_in_hand if not p.is_all_in()]
        if len(players_who_can_act) != 1:
            return False

        max_invested = BettingCalculator.get_max_invested_this_hand(players_in_hand)
        player = players_who_can_act[0]
        call_amount = BettingCalculator.calculate_call_amount(
            max_invested, player.total_invested_this_hand
        )
        return call_amount.value == 0

    @staticmethod
    def is_tournament_complete(game: Game) -> bool:
        """Check if the tournament is complete (only one player has chips remaining)."""
        return len(game.get_active_players()) == 1
