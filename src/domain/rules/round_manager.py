from __future__ import annotations

from copy import deepcopy

from src.domain.models.card import Card
from src.domain.models.chips import ChipAmount
from src.domain.models.deck import Deck
from src.domain.models.game import BettingState, Game, GamePhase, HandState
from src.domain.models.player import Player
from src.domain.models.players import Players
from src.domain.models.position import TablePositionMapping
from src.domain.models.pot import PotState
from src.domain.models.seat import Seat
from src.domain.rules.position_manager import PositionManager
from src.domain.rules.pot_calculator import PotCalculator


class RoundManager:
    @staticmethod
    def advance(game: Game) -> Game:
        players_in_hand: list[Player] = list(game.players_in_hand())
        if not players_in_hand:
            raise ValueError("Cannot advance betting round: no players in hand")

        # Get ALL players with investments for pot calculation (including folded)
        all_players_with_investments = game.players.get_all_players_invested_in_current_hand()

        updated_pot_state: PotState = PotCalculator.calculate_pot_state(
            all_players_with_investments
        )

        updated_players: Players = game.players.transform_all(lambda p: p.reset_for_new_round())

        next_phase: GamePhase | None = game.hand_state.current_phase.next_phase()
        if next_phase is None:
            raise ValueError(f"Cannot advance beyond {game.hand_state.current_phase}")

        updated_community_cards: list[Card] = list(game.hand_state.community_cards)
        updated_hand_state: HandState = HandState(
            hand_number=game.hand_state.hand_number,
            current_phase=next_phase,
            community_cards=updated_community_cards,
            is_initial_hand_setup=game.hand_state.is_initial_hand_setup,
        )

        position_mapping: TablePositionMapping = PositionManager.resolve_positions_for_hand(
            all_players=list(updated_players),
            previous_button_seat=game.button_seat,
            advance_button=False,  # Same hand, don't advance
        )
        players_in_hand_for_next_phase: tuple[Player, ...] = updated_players.in_hand()
        betting_order: list[Seat] = PositionManager.get_betting_order(
            position_mapping, next_phase, list(players_in_hand_for_next_phase)
        )
        next_position_to_act: int = PositionManager.find_first_position_to_act(
            betting_order, updated_players
        )

        updated_betting_state: BettingState = BettingState(
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
            outcome=game.outcome,
        )

    @staticmethod
    def deal_community_cards(game: Game, deck: Deck) -> tuple[Game, Deck]:
        current_phase = game.hand_state.current_phase

        if current_phase == GamePhase.PRE_FLOP:
            raise ValueError("Cannot deal community cards: preflop has no community cards")
        if current_phase == GamePhase.SHOWDOWN:
            raise ValueError("Cannot deal community cards: already at showdown")

        next_phase = current_phase.next_phase()
        if next_phase is None:
            raise ValueError(f"Cannot deal community cards: no next phase after {current_phase}")

        current_card_count = len(game.hand_state.community_cards)
        target_card_count = current_phase.card_count
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
            is_initial_hand_setup=game.hand_state.is_initial_hand_setup,
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
            outcome=game.outcome,
        )

        return updated_game, updated_deck
