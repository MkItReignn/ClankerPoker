from __future__ import annotations

from dataclasses import replace

import structlog

from src.domain.models.chips import ChipAmount
from src.domain.models.game import Game, GamePhase, GameResults
from src.domain.models.player import (BettingRoundActionStatus,
                                      HandParticipationStatus, Player,
                                      PlayerId)
from src.domain.models.players import Players
from src.domain.models.pot import Pot, PotState
from src.domain.rules.chip_distributor import ChipDistributor
from src.domain.rules.hand_evaluator import HandEvaluation, HandEvaluator
from src.domain.rules.pot_calculator import PotCalculator
from src.logger.factories import get_generic_logger


class HandCompleter:
    _logger: structlog.BoundLogger = get_generic_logger(__name__.removeprefix("src."))

    @staticmethod
    def _determine_winners_by_pot(
        game: Game,
        players_in_hand: list[Player],
    ) -> dict[Pot, list[Player]]:
        # Validate that all players in hand have hole cards
        for player in players_in_hand:
            if player.hole_cards is None:
                raise ValueError(
                    f"Invalid game state: Player {player.id} is in hand but has no hole cards. "
                    f"This indicates a bug in game state management."
                )

        all_pots: list[Pot] = [game.pot_state.main_pot, *game.pot_state.side_pots]
        winners_by_pot: dict[Pot, list[Player]] = {}

        for pot in all_pots:
            eligible_players: list[Player] = [
                p for p in players_in_hand if p.id in pot.eligible_player_ids
            ]

            if not eligible_players:
                continue

            if len(eligible_players) == 1:
                winners_by_pot[pot] = eligible_players
                continue

            evaluations: list[tuple[Player, HandEvaluation]] = []
            for player in eligible_players:
                if player.hole_cards is None:
                    continue
                evaluation: HandEvaluation = HandEvaluator.evaluate_hand_strength(
                    player.hole_cards, game.community_cards
                )
                evaluations.append((player, evaluation))

            if not evaluations:
                raise ValueError(
                    f"No hand evaluations available for pot of {pot.amount.value} chips. "
                    f"Eligible players: {list(pot.eligible_player_ids)}. "
                    f"Players in hand: {[p.id for p in eligible_players]}. "
                    f"This indicates a critical bug in pot distribution logic."
                )

            best_evaluation: HandEvaluation = evaluations[0][1]
            for _, evaluation in evaluations[1:]:
                if evaluation.compare(best_evaluation) > 0:
                    best_evaluation = evaluation

            winners: list[Player] = [
                player
                for player, evaluation in evaluations
                if evaluation.compare(best_evaluation) == 0
            ]

            if winners:
                winners_by_pot[pot] = winners

        return winners_by_pot

    @staticmethod
    def _mark_eliminated_players(players: Players, hand_number: int) -> Players:
        """Mark players with 0 chips as eliminated and assign finish positions.

        Implements SIMUL-001 through SIMUL-004:
        - Multiple players can bust on the same hand
        - Higher starting stack = better (lower) finish position
        - Equal starting stacks = same finish position (tie)
        - Uses stack at hand START for tiebreaker
        """
        # Count active players before marking eliminations
        active_count = len(players.active())

        # Find players being eliminated this hand
        newly_eliminated: list[Player] = [
            p
            for p in players
            if p.remaining_chips.value == 0
            and p.participation_status != HandParticipationStatus.ELIMINATED
        ]

        if not newly_eliminated:
            return players

        # Sort by stack_at_hand_start DESCENDING (larger stack = better position)
        # Use 0 as fallback if stack_at_hand_start is None (shouldn't happen)
        newly_eliminated.sort(
            key=lambda p: p.stack_at_hand_start.value if p.stack_at_hand_start else 0,
            reverse=True,
        )

        # Assign finish positions with tiebreaker logic
        # Positions range from (active_count - len(newly_eliminated) + 1) to active_count
        # Best eliminated player gets lowest position number (best finish)
        player_updates: dict[str, Player] = {}
        current_position = active_count - len(newly_eliminated) + 1
        prev_stack: int | None = None
        prev_position: int = current_position

        for player in newly_eliminated:
            stack_value = player.stack_at_hand_start.value if player.stack_at_hand_start else 0

            # If same stack as previous player, assign same position (tie)
            if prev_stack is not None and stack_value == prev_stack:
                position = prev_position
            else:
                position = current_position
                prev_position = position

            player_updates[player.id] = replace(
                player,
                participation_status=HandParticipationStatus.ELIMINATED,
                elimination_hand_number=hand_number,
                betting_status=BettingRoundActionStatus.ACTED,
                table_finish_position=position,
            )

            prev_stack = stack_value
            current_position += 1

        return players.replace_all(player_updates)

    @staticmethod
    def complete(game: Game) -> Game:
        if not game.is_hand_complete():
            raise ValueError("Cannot complete hand: hand is not yet complete")

        players_in_hand = list(game.players_in_hand())

        if len(players_in_hand) == 1:
            return HandCompleter._complete_early_win(game, players_in_hand[0])

        if game.current_phase == GamePhase.SHOWDOWN:
            return HandCompleter._complete_showdown(game, players_in_hand)

        raise ValueError(
            f"Cannot complete hand: invalid state - phase={game.current_phase.value}, "
            + f"players_in_hand={len(players_in_hand)}"
        )

    @staticmethod
    def _complete_early_win(game: Game, winner: Player) -> Game:
        # Always recalculate pot to ensure correctness
        # (No uncalled returns in early win - only 1 player remains)
        all_players_with_investments = game.players.get_all_players_invested_in_current_hand()

        if all_players_with_investments:
            updated_pot_state = PotCalculator.calculate_pot_state(all_players_with_investments)
            total_pot = updated_pot_state.total_amount()
        else:
            HandCompleter._logger.error(
                "Invalid game state: pot exists but no players have investments",
                hand_number=game.hand_state.hand_number,
                pot_total=game.pot_state.total_amount().value,
                players_count=len(game.players),
            )
            raise ValueError(
                "Invalid game state: pot exists but no players have investments. "
                "This indicates a critical bug in game state management."
            )

        updated_winner = replace(
            winner,
            remaining_chips=ChipAmount(winner.remaining_chips.value + total_pot.value),
        )

        updated_players = game.players.replace_player(winner.id, updated_winner)
        updated_players = HandCompleter._mark_eliminated_players(
            updated_players, game.hand_state.hand_number
        )

        updated_results = GameResults(
            hand_number=game.hand_state.hand_number,
            winners=[(winner.id, total_pot)],
        )

        return Game(
            identity=game.identity,
            tournament_config=game.tournament_config,
            hand_state=game.hand_state,
            pot_state=updated_pot_state,
            betting_state=game.betting_state,
            button_seat=game.button_seat,
            blind_state=game.blind_state,
            players=updated_players,
            results=updated_results,
        )

    @staticmethod
    def _complete_showdown(game: Game, players_in_hand: list[Player]) -> Game:
        uncalled_returns: dict[PlayerId, ChipAmount] = (
            ChipDistributor.calculate_uncalled_bet_returns(players_in_hand)
        )

        # Always recalculate pot after adjusting for uncalled returns
        # This ensures pot structure is correct regardless of when hand completes
        all_players: list[Player] = list(game.players)
        adjusted_all_players: list[Player] = []

        for player in all_players:
            if player.id in uncalled_returns:
                adjusted_investment = (
                    player.total_invested_this_hand.value - uncalled_returns[player.id].value
                )
                adjusted_player: Player = replace(
                    player,
                    total_invested_this_hand=ChipAmount(adjusted_investment),
                )
                adjusted_all_players.append(adjusted_player)
            else:
                adjusted_all_players.append(player)

        # Filter to only players with investments for pot calculation
        adjusted_players_with_investments: list[Player] = [
            p for p in adjusted_all_players if p.total_invested_this_hand.value > 0
        ]

        updated_pot_state: PotState = PotCalculator.calculate_pot_state(
            adjusted_players_with_investments
        )

        game_with_updated_pots = Game(
            identity=game.identity,
            tournament_config=game.tournament_config,
            hand_state=game.hand_state,
            pot_state=updated_pot_state,
            betting_state=game.betting_state,
            button_seat=game.button_seat,
            blind_state=game.blind_state,
            players=game.players,
            results=game.results,
        )

        winners_by_pot = HandCompleter._determine_winners_by_pot(
            game_with_updated_pots, players_in_hand
        )

        pot_payouts = ChipDistributor.distribute_all_pots(
            pot_state=updated_pot_state,
            winners_by_pot=winners_by_pot,
            button_seat=game.button_seat,
            all_players=list(game.players),
        )

        # Apply uncalled returns and pot winnings
        player_updates: dict[str, Player] = {}
        for player in game.players:
            new_chips = player.remaining_chips.value

            if player.id in uncalled_returns:
                new_chips += uncalled_returns[player.id].value

            if player.id in pot_payouts:
                new_chips += pot_payouts[player.id].value

            if new_chips != player.remaining_chips.value:
                player_updates[player.id] = replace(
                    player,
                    remaining_chips=ChipAmount(new_chips),
                )

        updated_players = (
            game.players.replace_all(player_updates) if player_updates else game.players
        )
        updated_players = HandCompleter._mark_eliminated_players(
            updated_players, game.hand_state.hand_number
        )

        winners = [(pid, payout) for pid, payout in pot_payouts.items()]

        updated_results = GameResults(
            hand_number=game.hand_state.hand_number,
            winners=winners,
        )

        return Game(
            identity=game.identity,
            tournament_config=game.tournament_config,
            hand_state=game.hand_state,
            pot_state=updated_pot_state,
            betting_state=game.betting_state,
            button_seat=game.button_seat,
            blind_state=game.blind_state,
            players=updated_players,
            results=updated_results,
        )
