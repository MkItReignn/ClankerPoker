from __future__ import annotations

from copy import deepcopy

from src.domain.models.card import Card
from src.domain.models.deck import Deck
from src.domain.models.game import Game
from src.domain.models.player import Player


class GameOrchestrator:
    """
    Orchestrates game-level operations.

    Handles:
    - initialize_game: High card draw for initial button assignment
    - is_game_complete: Check if tournament is over (one player remaining)
    """

    @staticmethod
    def _compare_cards_for_high_card_draw(card1: Card, card2: Card) -> int:
        """
        Compare two cards for high card draw.

        Per RULE_BOOK Section 14.1:
        - Higher rank wins
        - If same rank, suit tiebreaker: Spades > Hearts > Diamonds > Clubs

        Returns:
            Positive if card1 wins, negative if card2 wins, 0 if equal (shouldn't happen)
        """
        if card1.rank.value != card2.rank.value:
            return card1.rank.value - card2.rank.value
        return card1.suit.ranking - card2.suit.ranking

    @staticmethod
    def _find_high_card_winner(player_cards: list[tuple[Player, Card]]) -> Player:
        """Find the player with the highest card."""
        if not player_cards:
            raise ValueError("Cannot find winner: no players")

        winner, best_card = player_cards[0]
        for player, card in player_cards[1:]:
            if GameOrchestrator._compare_cards_for_high_card_draw(card, best_card) > 0:
                winner = player
                best_card = card

        return winner

    @staticmethod
    def initialize_game(game: Game, deck: Deck) -> tuple[Game, Deck]:
        """
        Initialize game with high card draw for initial button assignment.

        Per RULE_BOOK Section 14.1:
        - Each player receives one card face-up from a shuffled deck
        - Highest card receives the dealer button
        - Suit tiebreaker: Spades > Hearts > Diamonds > Clubs

        Returns:
            (updated_game_with_button_set, updated_deck)
        """
        active_players = game.get_active_players()
        if len(active_players) < 2:
            raise ValueError(
                f"Cannot initialize game: need at least 2 players, got {len(active_players)}"
            )

        updated_deck = deepcopy(deck)

        player_cards: list[tuple[Player, Card]] = []
        for player in active_players:
            card = updated_deck.deal_card()
            player_cards.append((player, card))

        winner = GameOrchestrator._find_high_card_winner(player_cards)

        updated_game = Game(
            identity=game.identity,
            tournament_config=game.tournament_config,
            hand_state=game.hand_state,
            pot_state=game.pot_state,
            betting_state=game.betting_state,
            button_seat=winner.seat,
            blind_state=game.blind_state,
            players=game.players,
            results=game.results,
        )

        return updated_game, updated_deck

    @staticmethod
    def is_game_complete(game: Game) -> bool:
        """
        Check if the tournament is complete.

        Tournament ends when only one player has chips remaining.
        """
        active_players = game.get_active_players()
        return len(active_players) <= 1
