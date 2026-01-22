from __future__ import annotations

from src.domain.models.deck import Deck
from src.domain.models.game import Game
from src.domain.rules.hand_completer import HandCompleter
from src.domain.rules.hand_initializer import HandInitializer
from src.domain.rules.round_manager import RoundManager


class HandEngine:
    """
    Hand-level orchestrator.

    Provides a unified API for hand operations by delegating to specialized modules:
    - HandInitializer: Hand setup (deal cards, post blinds)
    - RoundManager: Betting round transitions and community cards
    - HandCompleter: Hand completion and chip distribution
    """

    @staticmethod
    def setup_hand(game: Game, deck: Deck) -> tuple[Game, Deck]:
        return HandInitializer.setup_hand(game, deck)

    @staticmethod
    def post_blinds(game: Game) -> Game:
        return HandInitializer.post_blinds(game)

    @staticmethod
    def advance_betting_round(game: Game) -> Game:
        return RoundManager.advance(game)

    @staticmethod
    def deal_community_cards(game: Game, deck: Deck) -> tuple[Game, Deck]:
        return RoundManager.deal_community_cards(game, deck)

    @staticmethod
    def complete_hand(game: Game) -> Game:
        return HandCompleter.complete(game)
