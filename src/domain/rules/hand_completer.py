from __future__ import annotations

from dataclasses import replace

import structlog

from src.domain.models.chips import ChipAmount
from src.domain.models.game import Game, GamePhase, GameResults
from src.domain.models.player import (BettingRoundActionStatus,
                                      HandParticipationStatus, Player,
                                      PlayerId)
from src.domain.models.players import Players
from src.domain.models.pot import Pot
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
        def mark_if_eliminated(player: Player) -> Player:
            if (
                player.remaining_chips.value == 0
                and player.participation_status != HandParticipationStatus.ELIMINATED
            ):
                return replace(
                    player,
                    participation_status=HandParticipationStatus.ELIMINATED,
                    elimination_hand_number=hand_number,
                    betting_status=BettingRoundActionStatus.ACTED,
                )
            return player

        return players.transform_all(mark_if_eliminated)

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
        total_pot = game.pot_state.total_amount()

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
            pot_state=game.pot_state,
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

        # Create adjusted players for pot calculation
        adjusted_players_in_hand: list[Player] = []
        for player in players_in_hand:
            if player.id in uncalled_returns:
                adjusted_investment = (
                    player.total_invested_this_hand.value - uncalled_returns[player.id].value
                )
                adjusted_player = replace(
                    player,
                    total_invested_this_hand=ChipAmount(adjusted_investment),
                )
                adjusted_players_in_hand.append(adjusted_player)
            else:
                adjusted_players_in_hand.append(player)

        updated_pot_state = PotCalculator.calculate_pot_state(adjusted_players_in_hand)

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
