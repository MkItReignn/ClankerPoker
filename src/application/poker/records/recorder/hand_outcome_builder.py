"""Builder for hand outcome records."""

from __future__ import annotations

from src.application.poker.records.models import (HandOutcome, PlayerOutcome,
                                                  ShowdownResult)
from src.config.poker.config import PokerPlayerConfig
from src.domain.models.chips import ChipAmount
from src.domain.models.game import Game, GamePhase
from src.domain.models.player import HandParticipationStatus
from src.domain.rules.hand_evaluator import HandEvaluator


class HandOutcomeBuilder:
    """Builds HandOutcome from game state after hand completion."""

    def __init__(self, player_configs: dict[str, PokerPlayerConfig]) -> None:
        self._player_configs = player_configs

    def build(self, state: Game) -> HandOutcome:
        """Build hand outcome from game state.

        Raises:
            ValueError: If called before eliminated players have been marked.
        """
        self._validate_eliminations_marked(state)

        winner_ids = self._extract_winner_ids(state)
        total_pot = self._calculate_total_pot(state)
        was_showdown = self._is_showdown(state)
        showdown_results = self._build_showdown_results(state) if was_showdown else []
        player_outcomes = self._build_player_outcomes(state)

        return HandOutcome(
            winner_ids=tuple(winner_ids) if winner_ids else ("unknown",),
            pot_amount=total_pot,
            was_showdown=was_showdown,
            showdown_results=tuple(showdown_results),
            player_outcomes=tuple(player_outcomes),
        )

    def _validate_eliminations_marked(self, state: Game) -> None:
        """Validate that players with 0 chips have been marked as eliminated.

        This ensures the builder is called after HandCompleter.complete(),
        which is responsible for marking eliminations.
        """
        for player in state.players:
            if (
                player.remaining_chips.value == 0
                and player.participation_status != HandParticipationStatus.ELIMINATED
            ):
                raise ValueError(
                    f"Player '{player.id}' has 0 chips but is not marked as eliminated. "
                    f"HandOutcomeBuilder.build() must be called after "
                    f"HandCompleter.complete() has marked eliminations."
                )

    def _get_player_name(self, player_id: str) -> str:
        if player_id not in self._player_configs:
            raise KeyError(f"Player ID '{player_id}' not found in player_configs")
        return self._player_configs[player_id].name

    def _extract_winner_ids(self, state: Game) -> list[str]:
        if state.outcome is None:
            return []
        return [w[0] for w in state.outcome.winners]

    def _calculate_total_pot(self, state: Game) -> ChipAmount:
        if state.outcome is None or not state.outcome.winners:
            return state.pot
        return sum((w[1] for w in state.outcome.winners), start=ChipAmount(0))

    def _is_showdown(self, state: Game) -> bool:
        players_in_hand = state.players_in_hand()
        return len(players_in_hand) > 1 and state.current_phase == GamePhase.SHOWDOWN

    def _build_showdown_results(self, state: Game) -> list[ShowdownResult]:
        community_cards = state.community_cards
        if len(community_cards) != 5:
            raise ValueError(
                f"Showdown requires exactly 5 community cards, got {len(community_cards)}"
            )

        results: list[ShowdownResult] = []
        for player in state.players_in_hand():
            if player.hole_cards is not None:
                hand_evaluation = HandEvaluator.evaluate_hand_strength(
                    player.hole_cards, community_cards
                )
                results.append(
                    ShowdownResult(
                        player_id=player.id,
                        player_name=self._get_player_name(player.id),
                        hole_cards=player.hole_cards,
                        hand_evaluation=hand_evaluation,
                    )
                )
        return results

    def _build_player_outcomes(self, state: Game) -> list[PlayerOutcome]:
        outcomes: list[PlayerOutcome] = []
        current_hand = state.hand_state.hand_number

        for player in state.players:
            # Skip players eliminated in previous hands
            if (
                player.elimination_hand_number is not None
                and player.elimination_hand_number != current_hand
            ):
                continue

            chips_won = self._get_chips_won(player.id, state)
            was_eliminated = player.elimination_hand_number == current_hand

            outcomes.append(
                PlayerOutcome(
                    player_id=player.id,
                    player_name=self._get_player_name(player.id),
                    chips_won=chips_won,
                    final_stack=player.remaining_chips,
                    was_eliminated=was_eliminated,
                )
            )
        return outcomes

    def _get_chips_won(self, player_id: str, state: Game) -> ChipAmount:
        if state.outcome is None:
            return ChipAmount(0)
        for w_id, w_amount in state.outcome.winners:
            if w_id == player_id:
                return w_amount
        return ChipAmount(0)
