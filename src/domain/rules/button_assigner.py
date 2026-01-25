from src.domain.models.card import Card
from src.domain.models.deck import Deck
from src.domain.models.game import Game
from src.domain.models.player import Player
from src.domain.utils.seed_sequence import SeedSequence


class ButtonAssigner:
    """Determines initial dealer button position via high card draw."""

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
    def _find_high_card_winner(
        player_cards: list[tuple[Player, Card]]
    ) -> Player:
        """Find the player with the highest card."""
        if not player_cards:
            raise ValueError("Cannot find winner: no players")

        winner, best_card = player_cards[0]
        for player, card in player_cards[1:]:
            if (
                ButtonAssigner._compare_cards_for_high_card_draw(
                    card, best_card
                )
                > 0
            ):
                winner = player
                best_card = card

        return winner

    @staticmethod
    def assign_button(game: Game) -> Game:
        """
        Assign initial button via high card draw.

        Per RULE_BOOK Section 14.1:
        - Each player receives one card face-up from a shuffled deck
        - Highest card receives the dealer button
        - Suit tiebreaker: Spades > Hearts > Diamonds > Clubs

        The deck is created deterministically using the game's seed (seed sequence index 0).

        Args:
            game: The game state to initialize.

        Returns:
            Updated game with button_seat assigned based on high card draw.
        """
        active_players = game.get_active_players()
        if len(active_players) < 2:
            raise ValueError(
                f"Cannot assign button: need at least 2 players, got {len(active_players)}"
            )

        # Create deck deterministically using seed sequence index 0
        seed_sequence = SeedSequence(base_seed=game.identity.seed)
        shuffle_seed = seed_sequence.get_shuffle_seed_for_button_init()
        deck = Deck.create_shuffled(seed=shuffle_seed)

        player_cards: list[tuple[Player, Card]] = []
        for player in active_players:
            card = deck.deal_card()
            player_cards.append((player, card))

        winner = ButtonAssigner._find_high_card_winner(player_cards)

        updated_game = Game(
            identity=game.identity,
            tournament_config=game.tournament_config,
            hand_state=game.hand_state,
            pot_state=game.pot_state,
            betting_state=game.betting_state,
            button_seat=winner.seat,
            blind_state=game.blind_state,
            players=game.players,
            outcome=game.outcome,
        )

        return updated_game
