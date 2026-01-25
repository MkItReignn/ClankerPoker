from src.application.poker.state_observers.details import (
    EliminatedInfo,
    HandOutcomeDetails,
    PlayerOutcome,
    ShowdownResult,
    WinnerInfo,
)
from src.domain.models.chips import ChipAmount
from src.domain.models.game import Game, HandPhase
from src.domain.models.player import HandParticipationStatus, Player
from src.domain.rules.hand_evaluator import HandEvaluator


class HandOutcomeBuilder:
    @staticmethod
    def build(game: Game) -> HandOutcomeDetails:
        HandOutcomeBuilder._validate_eliminations_marked(game)

        winners: tuple[WinnerInfo, ...] = HandOutcomeBuilder._derive_winners(
            game
        )
        eliminated: tuple[EliminatedInfo, ...] = (
            HandOutcomeBuilder._derive_eliminated(game)
        )
        showdown: tuple[ShowdownResult, ...] | None = (
            HandOutcomeBuilder._derive_showdown(game)
        )
        pot_amount: ChipAmount = HandOutcomeBuilder._calculate_pot_amount(game)
        player_outcomes: tuple[PlayerOutcome, ...] = (
            HandOutcomeBuilder._derive_player_outcomes(game)
        )

        return HandOutcomeDetails(
            winners=winners,
            eliminated=eliminated,
            showdown=showdown,
            pot_amount=pot_amount,
            player_outcomes=player_outcomes,
        )

    @staticmethod
    def _validate_eliminations_marked(game: Game) -> None:
        player: Player
        for player in game.players:
            if (
                player.remaining_chips.value == 0
                and player.participation_status
                != HandParticipationStatus.ELIMINATED
            ):
                raise ValueError(
                    f"Player '{player.id}' has 0 chips but is not marked as eliminated. "
                    f"HandOutcomeBuilder.build() must be called after "
                    f"HandCompleter.complete() has marked eliminations."
                )

    @staticmethod
    def _derive_winners(game: Game) -> tuple[WinnerInfo, ...]:
        if game.outcome is None:
            raise ValueError("Cannot derive winners: game.outcome is None")

        winners: list[WinnerInfo] = []
        player_id: str
        amount: ChipAmount
        for player_id, amount in game.outcome.winners:
            player: Player | None = game.players.get_by_id(player_id)
            if player:
                winners.append(
                    WinnerInfo(
                        player_id=player_id,
                        player_name=player.name,
                        amount=amount,
                    )
                )
        return tuple(winners)

    @staticmethod
    def _derive_eliminated(game: Game) -> tuple[EliminatedInfo, ...]:
        eliminated: list[EliminatedInfo] = []
        current_hand: int = game.hand_state.hand_number

        player: Player
        for player in game.players:
            if (
                player.elimination_hand_number == current_hand
                and player.table_finish_position is not None
            ):
                eliminated.append(
                    EliminatedInfo(
                        player_id=player.id,
                        player_name=player.name,
                        finish_position=player.table_finish_position,
                    )
                )
        return tuple(eliminated)

    @staticmethod
    def _derive_showdown(game: Game) -> tuple[ShowdownResult, ...] | None:
        if game.current_phase != HandPhase.SHOWDOWN:
            return None

        showdown_players: list[Player] = [
            p
            for p in game.players
            if p.hole_cards is not None
            and p.participation_status
            in (
                HandParticipationStatus.IN_HAND,
                HandParticipationStatus.ELIMINATED,
            )
        ]

        if len(showdown_players) <= 1:
            return None

        community_cards = game.community_cards
        if len(community_cards) != 5:
            raise ValueError(
                f"Showdown requires exactly 5 community cards, got {len(community_cards)}"
            )

        results: list[ShowdownResult] = []
        for player in showdown_players:
            hole_cards = player.hole_cards
            if hole_cards is None:
                continue
            hand_evaluation = HandEvaluator.evaluate_hand_strength(
                hole_cards, community_cards
            )
            results.append(
                ShowdownResult(
                    player_id=player.id,
                    player_name=player.name,
                    hole_cards=hole_cards,
                    hand_evaluation=hand_evaluation,
                )
            )
        return tuple(results) if results else None

    @staticmethod
    def _calculate_pot_amount(game: Game) -> ChipAmount:
        if game.outcome is None or not game.outcome.winners:
            return game.pot
        return sum((w[1] for w in game.outcome.winners), start=ChipAmount(0))

    @staticmethod
    def _derive_player_outcomes(game: Game) -> tuple[PlayerOutcome, ...]:
        outcomes: list[PlayerOutcome] = []
        current_hand: int = game.hand_state.hand_number

        player: Player
        for player in game.players:
            if (
                player.elimination_hand_number is not None
                and player.elimination_hand_number != current_hand
            ):
                continue

            chips_won: ChipAmount = HandOutcomeBuilder._get_chips_won(
                player.id, game
            )

            outcomes.append(
                PlayerOutcome(
                    player_id=player.id,
                    player_name=player.name,
                    chips_won=chips_won,
                    final_stack=player.remaining_chips,
                )
            )
        return tuple(outcomes)

    @staticmethod
    def _get_chips_won(player_id: str, game: Game) -> ChipAmount:
        if game.outcome is None:
            return ChipAmount(0)
        w_id: str
        w_amount: ChipAmount
        for w_id, w_amount in game.outcome.winners:
            if w_id == player_id:
                return w_amount
        return ChipAmount(0)
