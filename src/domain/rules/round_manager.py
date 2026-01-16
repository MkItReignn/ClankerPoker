from __future__ import annotations

from copy import deepcopy

from src.domain.models.chips import ChipAmount
from src.domain.models.deck import Deck
from src.domain.models.game import (
    NO_POSITION_TO_ACT,
    BettingState,
    Game,
    GamePhase,
    HandState,
)
from src.domain.rules.position_manager import PositionManager
from src.domain.rules.pot_calculator import PotCalculator


class RoundManager:
    @staticmethod
    def advance(game: Game) -> Game:
        players_in_hand = list(game.players_in_hand())
        if not players_in_hand:
            raise ValueError("Cannot advance betting round: no players in hand")

        updated_pot_state = PotCalculator.calculate_pot_state(players_in_hand)

        updated_players = game.players.transform_all(lambda p: p.reset_for_new_round())

        next_phase = game.hand_state.current_phase.next_phase()
        if next_phase is None:
            raise ValueError(f"Cannot advance beyond {game.hand_state.current_phase}")

        cards_to_deal = next_phase.card_count - len(game.hand_state.community_cards)
        if cards_to_deal > 0:
            raise ValueError(
                "Cannot advance betting round: community cards must be dealt externally"
            )

        updated_community_cards = list(game.hand_state.community_cards)
        updated_hand_state = HandState(
            hand_number=game.hand_state.hand_number,
            current_phase=next_phase,
            community_cards=updated_community_cards,
            is_first_hand=game.hand_state.is_first_hand,
        )

        position_mapping = PositionManager.resolve_positions_for_new_hand(
            all_players=list(updated_players),
            previous_button_seat=game.button_seat,
            is_first_hand=False,
        )
        players_in_hand_for_next_phase = [p for p in updated_players if p.is_in_hand()]
        betting_order = PositionManager.get_betting_order(
            position_mapping, next_phase, players_in_hand_for_next_phase
        )
        next_position_to_act = NO_POSITION_TO_ACT
        for seat in betting_order:
            player = updated_players.get_by_seat(seat)
            if player and not player.is_all_in():
                next_position_to_act = seat.value
                break

        updated_betting_state = BettingState(
            last_raise_increment=ChipAmount(0),
            position_to_act=next_position_to_act,
        )

        return Game(
            identity=game.identity,
            tournament_config=game.tournament_config,
            hand_state=updated_hand_state,
            pot_state=updated_pot_state,
            betting_state=updated_betting_state,
            button_seat=game.button_seat,
            blind_state=game.blind_state,
            players=updated_players,
            results=game.results,
        )

    @staticmethod
    def deal_community_cards(game: Game, deck: Deck) -> tuple[Game, Deck]:
        current_phase = game.hand_state.current_phase
        next_phase = current_phase.next_phase()

        if next_phase is None:
            raise ValueError(f"Cannot deal community cards: no next phase after {current_phase}")

        if next_phase == GamePhase.SHOWDOWN:
            raise ValueError("Cannot deal community cards: already at river")

        current_card_count = len(game.hand_state.community_cards)
        target_card_count = next_phase.card_count
        cards_to_deal = target_card_count - current_card_count

        if cards_to_deal <= 0:
            raise ValueError(
                f"Cannot deal community cards: already have {current_card_count} cards "
                + f"for phase requiring {target_card_count}"
            )

        updated_deck = deepcopy(deck)
        updated_deck.burn_card()
        new_cards = updated_deck.deal_cards(cards_to_deal)

        updated_community_cards = list(game.hand_state.community_cards) + new_cards
        updated_hand_state = HandState(
            hand_number=game.hand_state.hand_number,
            current_phase=current_phase,
            community_cards=updated_community_cards,
            is_first_hand=game.hand_state.is_first_hand,
        )

        updated_game = Game(
            identity=game.identity,
            tournament_config=game.tournament_config,
            hand_state=updated_hand_state,
            pot_state=game.pot_state,
            betting_state=game.betting_state,
            button_seat=game.button_seat,
            blind_state=game.blind_state,
            players=game.players,
            results=game.results,
        )

        return updated_game, updated_deck
