from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

from src.config.tournament.config import BlindScheduleConfig
from src.domain.models.blinds import BlindLevel
from src.domain.models.chips import ChipAmount
from src.domain.models.deck import Deck
from src.domain.models.game import (BettingState, BlindState, Game, GamePhase,
                                    HandState)
from src.domain.models.hand import Hand
from src.domain.models.player import (BettingRoundActionStatus,
                                      HandParticipationStatus, Player)
from src.domain.models.pot import Pot, PotState
from src.domain.rules.position_manager import PositionManager


class HandInitializer:
    @staticmethod
    def _get_blind_level_for_hand(
        hand_number: int, blind_schedule: BlindScheduleConfig | None
    ) -> BlindLevel:
        if blind_schedule is not None:
            return blind_schedule.get_blind_level_for_hand(hand_number)

        return BlindLevel(
            small_blind=ChipAmount(10),
            big_blind=ChipAmount(20),
            level=1,
        )

    @staticmethod
    def _post_blind(player: Player, blind_amount: ChipAmount) -> Player:
        blind_posted = min(blind_amount.value, player.remaining_chips.value)
        is_all_in = player.remaining_chips.value - blind_posted == 0

        return replace(
            player,
            remaining_chips=ChipAmount(player.remaining_chips.value - blind_posted),
            total_invested_this_hand=ChipAmount(blind_posted),
            betting_status=(
                BettingRoundActionStatus.ACTED
                if is_all_in
                else BettingRoundActionStatus.NEEDS_ACTION
            ),
        )

    @staticmethod
    def initialize(game: Game, deck: Deck) -> tuple[Game, Deck]:
        active_players = game.get_active_players()
        if len(active_players) < 2:
            raise ValueError(
                f"Cannot initialize hand: need at least 2 players, got {len(active_players)}"
            )

        updated_deck = deepcopy(deck)

        # Deal hole cards and reset players for new hand
        player_updates: dict[str, Player] = {}
        for player in game.players:
            if player.participation_status != HandParticipationStatus.ELIMINATED:
                card1 = updated_deck.deal_card()
                card2 = updated_deck.deal_card()
                updated_player = player.reset_for_new_hand(Hand(card1=card1, card2=card2))
                player_updates[player.id] = updated_player

        updated_players = game.players.replace_all(player_updates)

        if game.hand_state.is_initial_hand_setup:
            next_hand_number = 1
        else:
            next_hand_number = game.hand_state.hand_number + 1
        blind_level = HandInitializer._get_blind_level_for_hand(
            next_hand_number, game.tournament_config.blind_schedule
        )
        updated_blind_state = BlindState(current_blind_level=blind_level)

        position_mapping = PositionManager.resolve_positions_for_new_hand(
            all_players=list(updated_players),
            previous_button_seat=game.button_seat,
            is_initial_hand_setup=game.hand_state.is_initial_hand_setup,
        )

        small_blind_seat = position_mapping.small_blind_seat
        big_blind_seat = position_mapping.big_blind_seat

        # Post blinds
        sb_player = updated_players[small_blind_seat]
        bb_player = updated_players[big_blind_seat]

        updated_sb = HandInitializer._post_blind(sb_player, blind_level.small_blind)
        updated_bb = HandInitializer._post_blind(bb_player, blind_level.big_blind)

        updated_players = updated_players.replace_all(
            {
                updated_sb.id: updated_sb,
                updated_bb.id: updated_bb,
            }
        )

        updated_hand_state = HandState(
            hand_number=next_hand_number,
            current_phase=GamePhase.PRE_FLOP,
            community_cards=[],
            is_initial_hand_setup=False,
        )

        eligible_ids = game.get_active_player_ids()
        updated_pot_state = PotState(
            main_pot=Pot(amount=ChipAmount(0), eligible_player_ids=eligible_ids),
            side_pots=[],
        )

        players_in_hand = [p for p in updated_players if p.is_in_hand()]
        betting_order = PositionManager.get_betting_order(
            position_mapping, GamePhase.PRE_FLOP, players_in_hand
        )
        first_to_act = PositionManager.find_first_position_to_act(betting_order, updated_players)

        updated_betting_state = BettingState(
            last_raise_increment=ChipAmount(0),
            position_to_act=first_to_act,
        )

        return (
            Game(
                identity=game.identity,
                tournament_config=game.tournament_config,
                hand_state=updated_hand_state,
                pot_state=updated_pot_state,
                betting_state=updated_betting_state,
                button_seat=position_mapping.button_seat,
                blind_state=updated_blind_state,
                players=updated_players,
                results=game.results,
            ),
            updated_deck,
        )
