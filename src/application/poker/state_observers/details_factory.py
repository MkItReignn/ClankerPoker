from typing import Protocol

from src.application.poker.state_observers.details import (
    ActionAppliedDetails,
    BlindInfo,
    BlindsPostedDetails,
    FinalStanding,
    GameCompletedDetails,
    GameStartedDetails,
    HandOutcomeDetails,
    HandStartedDetails,
    HoleCardDealtDetail,
    HoleCardsDealtDetails,
    PlayerToActDetails,
    RoundCompletedDetails,
    RoundStartedDetails,
)
from src.application.poker.state_observers.hand_outcome_builder import (
    HandOutcomeBuilder,
)
from src.domain.models.actions import ActionType
from src.domain.models.available_action import AvailableActions
from src.domain.models.chips import ChipAmount
from src.domain.models.game import Game, HandPhase
from src.domain.models.narration import Narration
from src.domain.rules.available_action_calculator import (
    AvailableActionCalculator,
)
from src.domain.rules.position_manager import PositionManager


class HasActionTypeAndAmount(Protocol):
    @property
    def action_type(self) -> ActionType: ...

    @property
    def amount(self) -> ChipAmount | None: ...


class HasActionFields(Protocol):
    @property
    def action(self) -> HasActionTypeAndAmount: ...

    @property
    def narration(self) -> Narration | None: ...


class DetailsFactory:
    @staticmethod
    def game_started(game: Game) -> GameStartedDetails:
        return GameStartedDetails(
            player_count=len(game.players),
            starting_chips=game.tournament_config.starting_chip_stack,
        )

    @staticmethod
    def game_completed(game: Game) -> GameCompletedDetails:
        active_players = game.get_active_players()
        if not active_players:
            raise ValueError("Cannot complete game: no active players")
        winner = active_players[0]

        standings: list[FinalStanding] = [
            FinalStanding(
                player_id=winner.id,
                player_name=winner.name,
                finish_position=1,
                elimination_hand=None,
            )
        ]

        eliminated = [p for p in game.players if p.id != winner.id]
        eliminated.sort(key=lambda p: p.table_finish_position or 0)

        for player in eliminated:
            standings.append(
                FinalStanding(
                    player_id=player.id,
                    player_name=player.name,
                    finish_position=player.table_finish_position or 0,
                    elimination_hand=player.elimination_hand_number,
                )
            )

        return GameCompletedDetails(
            winner_id=winner.id,
            winner_name=winner.name,
            total_hands=game.hand_state.hand_number,
            final_standings=tuple(standings),
        )

    @staticmethod
    def hand_started(game: Game) -> HandStartedDetails:
        positions = PositionManager.resolve_positions_for_hand(
            all_players=list(game.players),
            previous_button_seat=game.button_seat,
            advance_button=False,
        )
        return HandStartedDetails(
            hand_number=game.hand_state.hand_number,
            button_seat=game.button_seat,
            sb_seat=positions.small_blind_seat,
            bb_seat=positions.big_blind_seat,
        )

    @staticmethod
    def hand_completed(game: Game) -> HandOutcomeDetails:
        return HandOutcomeBuilder.build(game)

    @staticmethod
    def round_started(game: Game) -> RoundStartedDetails:
        new_cards = DetailsFactory._derive_new_cards(game)
        return RoundStartedDetails(
            phase=game.current_phase,
            new_cards=new_cards,
        )

    @staticmethod
    def round_completed() -> RoundCompletedDetails:
        return RoundCompletedDetails()

    @staticmethod
    def blinds_posted(game: Game) -> BlindsPostedDetails:
        sb_player, bb_player = DetailsFactory._derive_blind_players(game)
        return BlindsPostedDetails(
            small_blind=BlindInfo(
                player_id=sb_player.id if sb_player else "",
                player_name=sb_player.name if sb_player else "",
                amount=(
                    sb_player.total_invested_this_hand
                    if sb_player
                    else game.current_blind_level.small_blind
                ),
            ),
            big_blind=BlindInfo(
                player_id=bb_player.id if bb_player else "",
                player_name=bb_player.name if bb_player else "",
                amount=(
                    bb_player.total_invested_this_hand
                    if bb_player
                    else game.current_blind_level.big_blind
                ),
            ),
        )

    @staticmethod
    def hole_cards_dealt(game: Game) -> HoleCardsDealtDetails:
        deal_order_map = DetailsFactory._derive_all_deal_orders(game)
        players_details: dict[str, HoleCardDealtDetail] = {}

        for player in game.players_in_hand():
            if player.hole_cards is not None:
                players_details[player.id] = HoleCardDealtDetail(
                    player_id=player.id,
                    player_name=player.name,
                    cards=player.hole_cards,
                    deal_order=deal_order_map.get(player.id, 0),
                )

        return HoleCardsDealtDetails(players=players_details)

    @staticmethod
    def player_to_act(game: Game) -> PlayerToActDetails:
        player_id = game.get_player_to_act_id()
        if player_id is None:
            raise ValueError("No player to act")

        player = game.players.get_by_id(player_id)
        if player is None:
            raise ValueError(f"Player {player_id} not found")

        available_actions = DetailsFactory._derive_available_actions(
            game, player_id
        )
        return PlayerToActDetails(
            player_id=player.id,
            player_name=player.name,
            available_actions=available_actions,
        )

    @staticmethod
    def action_applied(
        game: Game, player_id: str, response: HasActionFields
    ) -> ActionAppliedDetails:
        player = game.players.get_by_id(player_id)
        if player is None:
            raise ValueError(f"Player {player_id} not found")

        return ActionAppliedDetails(
            player_id=player.id,
            player_name=player.name,
            action_type=response.action.action_type,
            amount=response.action.amount,
            narration=response.narration,
        )

    # =========================================================================
    # Private derivation helpers
    # =========================================================================

    @staticmethod
    def _derive_new_cards(game: Game) -> tuple:
        match game.current_phase:
            case HandPhase.FLOP:
                return tuple(game.community_cards[0:3])
            case HandPhase.TURN:
                return (game.community_cards[3],)
            case HandPhase.RIVER:
                return (game.community_cards[4],)
            case _:
                return ()

    @staticmethod
    def _derive_blind_players(game: Game) -> tuple:
        positions = PositionManager.resolve_positions_for_hand(
            all_players=list(game.players),
            previous_button_seat=game.button_seat,
            advance_button=False,
        )
        sb_player = game.players.get_by_seat(positions.small_blind_seat)
        bb_player = game.players.get_by_seat(positions.big_blind_seat)
        return sb_player, bb_player

    @staticmethod
    def _derive_all_deal_orders(game: Game) -> dict[str, int]:
        positions = PositionManager.resolve_positions_for_hand(
            all_players=list(game.players),
            previous_button_seat=game.button_seat,
            advance_button=False,
        )
        players_in_hand = list(game.players_in_hand())
        betting_order = PositionManager.get_betting_order(
            position_mapping=positions,
            phase=HandPhase.PRE_FLOP,
            players_in_hand=players_in_hand,
        )

        deal_orders: dict[str, int] = {}
        for order, seat in enumerate(betting_order, start=1):
            player = game.players.get_by_seat(seat)
            if player is not None:
                deal_orders[player.id] = order

        return deal_orders

    @staticmethod
    def _derive_available_actions(
        game: Game, player_id: str
    ) -> tuple[AvailableActions, ...]:
        available = AvailableActionCalculator.calculate_available_actions(
            game, player_id
        )
        return tuple(available)
