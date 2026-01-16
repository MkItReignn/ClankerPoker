"""
Behavioral tests for GameOrchestrator.

Tests document RULE_BOOK Section 14.1 (Initial Button Assignment via High Card Draw)
and tournament completion logic.
"""

from __future__ import annotations

import pytest

from src.domain.models.card import Card, Rank, Suit
from src.domain.models.chips import ChipAmount
from src.domain.models.deck import STANDARD_DECK, Deck
from src.domain.models.player import HandParticipationStatus, PlayerId
from src.domain.models.seat import Seat
from src.domain.rules.game_orchestrator import GameOrchestrator


def create_deck_with_top_cards(top_cards: list[Card]) -> Deck:
    """
    Create a valid 52-card deck with specific cards on top.

    Fills remaining slots with cards from standard deck not in top_cards.
    """
    used_cards = set(top_cards)
    remaining_cards = [card for card in STANDARD_DECK if card not in used_cards]

    # Ensure we have exactly 52 unique cards
    all_cards = top_cards + remaining_cards[: 52 - len(top_cards)]

    if len(all_cards) != 52:
        raise ValueError(f"Expected 52 cards, got {len(all_cards)}")

    return Deck(cards=all_cards)


class TestInitializeGame:
    """
    Tests for initialize_game documenting RULE_BOOK Section 14.1.

    Per RULE_BOOK 14.1: Initial Button Assignment
    - Each player receives one card face-up from a shuffled deck
    - Highest card receives the dealer button
    - Higher rank wins
    - Suit tiebreaker: Spades > Hearts > Diamonds > Clubs
    """

    def test_assigns_button_to_player_with_highest_rank(
        self,
        minimal_game_factory,
        sample_player_factory,
    ):
        """Button goes to player with highest card rank."""
        # Arrange: Create game with 3 players
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)),  # Will get 5♠
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)),  # Will get K♥
            sample_player_factory(PlayerId("p3"), Seat.SEAT_2, ChipAmount(1000)),  # Will get 7♣
        ]
        game = minimal_game_factory(players)

        # Deck ordered: 5♠, K♥, 7♣ (King is highest)
        deck = create_deck_with_top_cards(
            [
                Card(suit=Suit.SPADES, rank=Rank.FIVE),
                Card(suit=Suit.HEARTS, rank=Rank.KING),
                Card(suit=Suit.CLUBS, rank=Rank.SEVEN),
            ]
        )

        # Act
        updated_game, updated_deck = GameOrchestrator.initialize_game(game, deck)

        # Assert: Player at SEAT_1 (who got King) should have button
        assert updated_game.button_seat == Seat.SEAT_1

    def test_suit_tiebreaker_when_ranks_are_equal(
        self,
        minimal_game_factory,
        sample_player_factory,
    ):
        """
        When players draw same rank, suit determines winner.

        RULE_BOOK 14.1: Suit tiebreaker order: Spades > Hearts > Diamonds > Clubs
        """
        # Arrange: All players draw Aces with different suits
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)),  # Will get A♦
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)),  # Will get A♠
            sample_player_factory(PlayerId("p3"), Seat.SEAT_2, ChipAmount(1000)),  # Will get A♣
        ]
        game = minimal_game_factory(players)

        # Deck: A♦, A♠, A♣ (Spades wins suit tiebreaker)
        deck = create_deck_with_top_cards(
            [
                Card(suit=Suit.DIAMONDS, rank=Rank.ACE),
                Card(suit=Suit.SPADES, rank=Rank.ACE),  # Highest suit
                Card(suit=Suit.CLUBS, rank=Rank.ACE),
            ]
        )

        # Act
        updated_game, updated_deck = GameOrchestrator.initialize_game(game, deck)

        # Assert: A♠ beats A♦ and A♣
        assert updated_game.button_seat == Seat.SEAT_1

    def test_hearts_beats_diamonds_in_suit_tiebreaker(
        self,
        minimal_game_factory,
        sample_player_factory,
    ):
        """Hearts > Diamonds per RULE_BOOK 14.1 suit ranking."""
        # Arrange
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)),  # Will get K♦
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)),  # Will get K♥
        ]
        game = minimal_game_factory(players)

        deck = create_deck_with_top_cards(
            [
                Card(suit=Suit.DIAMONDS, rank=Rank.KING),
                Card(suit=Suit.HEARTS, rank=Rank.KING),  # Hearts beats Diamonds
            ]
        )

        # Act
        updated_game, _ = GameOrchestrator.initialize_game(game, deck)

        # Assert
        assert updated_game.button_seat == Seat.SEAT_1

    def test_diamonds_beats_clubs_in_suit_tiebreaker(
        self,
        minimal_game_factory,
        sample_player_factory,
    ):
        """Diamonds > Clubs per RULE_BOOK 14.1 suit ranking."""
        # Arrange
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)),  # Will get Q♣
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)),  # Will get Q♦
        ]
        game = minimal_game_factory(players)

        deck = create_deck_with_top_cards(
            [
                Card(suit=Suit.CLUBS, rank=Rank.QUEEN),
                Card(suit=Suit.DIAMONDS, rank=Rank.QUEEN),  # Diamonds beats Clubs
            ]
        )

        # Act
        updated_game, _ = GameOrchestrator.initialize_game(game, deck)

        # Assert
        assert updated_game.button_seat == Seat.SEAT_1

    def test_works_with_minimum_two_players(
        self,
        minimal_game_factory,
        sample_player_factory,
    ):
        """Heads-up (2 players) is valid for initial button assignment."""
        # Arrange
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)),
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)),
        ]
        game = minimal_game_factory(players)

        deck = create_deck_with_top_cards(
            [
                Card(suit=Suit.CLUBS, rank=Rank.THREE),
                Card(suit=Suit.HEARTS, rank=Rank.NINE),  # Higher card
            ]
        )

        # Act
        updated_game, _ = GameOrchestrator.initialize_game(game, deck)

        # Assert: Player 2 with 9♥ wins
        assert updated_game.button_seat == Seat.SEAT_1

    def test_rejects_game_with_fewer_than_two_active_players(
        self,
        minimal_game_factory,
        sample_player_factory,
    ):
        """Cannot initialize with fewer than 2 active players per RULE_BOOK 14.1."""
        # Arrange: 2 players but 1 is eliminated
        players = [
            sample_player_factory(
                PlayerId("p1"),
                Seat.SEAT_0,
                ChipAmount(1000),
                participation_status=HandParticipationStatus.IN_HAND,
            ),
            sample_player_factory(
                PlayerId("p2"),
                Seat.SEAT_1,
                ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
        ]
        game = minimal_game_factory(players)
        deck = Deck.create_shuffled(seed=42)

        # Act & Assert: Only 1 active player (non-eliminated)
        with pytest.raises(ValueError, match="need at least 2 players"):
            GameOrchestrator.initialize_game(game, deck)

    def test_rejects_game_with_all_players_eliminated(
        self,
        minimal_game_factory,
        sample_player_factory,
    ):
        """Cannot initialize when all players are eliminated."""
        # Arrange: All players eliminated
        players = [
            sample_player_factory(
                PlayerId("p1"),
                Seat.SEAT_0,
                ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                PlayerId("p2"),
                Seat.SEAT_1,
                ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
        ]
        game = minimal_game_factory(players)
        deck = Deck.create_shuffled(seed=42)

        # Act & Assert: 0 active players
        with pytest.raises(ValueError, match="need at least 2 players"):
            GameOrchestrator.initialize_game(game, deck)

    def test_only_considers_active_players_for_high_card_draw(
        self,
        minimal_game_factory,
        sample_player_factory,
    ):
        """Eliminated players are excluded from high card draw."""
        # Arrange: 2 active players, 1 eliminated
        players = [
            sample_player_factory(
                PlayerId("p1"),
                Seat.SEAT_0,
                ChipAmount(1000),
                participation_status=HandParticipationStatus.IN_HAND,
            ),
            sample_player_factory(
                PlayerId("p2"),
                Seat.SEAT_1,
                ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                PlayerId("p3"),
                Seat.SEAT_2,
                ChipAmount(1000),
                participation_status=HandParticipationStatus.IN_HAND,
            ),
        ]
        game = minimal_game_factory(players)

        # Only p1 and p3 should receive cards (p2 is eliminated)
        deck = create_deck_with_top_cards(
            [
                Card(suit=Suit.CLUBS, rank=Rank.FIVE),  # p1
                Card(suit=Suit.SPADES, rank=Rank.KING),  # p3 (highest)
            ]
        )

        # Act
        updated_game, _ = GameOrchestrator.initialize_game(game, deck)

        # Assert: p3 (SEAT_2) should win
        assert updated_game.button_seat == Seat.SEAT_2

    def test_deals_one_card_per_active_player(
        self,
        minimal_game_factory,
        sample_player_factory,
    ):
        """Deck index advances by exactly the number of active players."""
        # Arrange
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)),
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)),
            sample_player_factory(PlayerId("p3"), Seat.SEAT_2, ChipAmount(1000)),
        ]
        game = minimal_game_factory(players)
        deck = Deck.create_shuffled(seed=42)
        initial_cards_remaining = deck.cards_remaining()

        # Act
        _, updated_deck = GameOrchestrator.initialize_game(game, deck)

        # Assert: 3 cards dealt
        assert updated_deck.cards_remaining() == initial_cards_remaining - 3

    def test_returns_updated_game_with_button_assigned(
        self,
        minimal_game_factory,
        sample_player_factory,
    ):
        """initialize_game returns new Game instance with button_seat set."""
        # Arrange
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)),
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)),
        ]
        game = minimal_game_factory(players)
        original_button = game.button_seat

        deck = create_deck_with_top_cards(
            [
                Card(suit=Suit.CLUBS, rank=Rank.TWO),
                Card(suit=Suit.SPADES, rank=Rank.ACE),  # Winner
            ]
        )

        # Act
        updated_game, _ = GameOrchestrator.initialize_game(game, deck)

        # Assert: New game instance with updated button
        assert updated_game is not game  # Immutable pattern
        assert updated_game.button_seat == Seat.SEAT_1
        assert updated_game.button_seat != original_button

    def test_preserves_other_game_state(
        self,
        minimal_game_factory,
        sample_player_factory,
    ):
        """initialize_game only modifies button_seat, preserving all other state."""
        # Arrange
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)),
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)),
        ]
        game = minimal_game_factory(players)
        deck = Deck.create_shuffled(seed=42)

        # Act
        updated_game, _ = GameOrchestrator.initialize_game(game, deck)

        # Assert: Everything except button_seat is preserved
        assert updated_game.identity == game.identity
        assert updated_game.tournament_config == game.tournament_config
        assert updated_game.hand_state == game.hand_state
        assert updated_game.pot_state == game.pot_state
        assert updated_game.betting_state == game.betting_state
        assert updated_game.blind_state == game.blind_state
        assert updated_game.players == game.players
        assert updated_game.results == game.results

    def test_ace_is_highest_card_in_high_card_draw(
        self,
        minimal_game_factory,
        sample_player_factory,
    ):
        """Ace beats all other ranks including King."""
        # Arrange
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)),  # Will get K♠
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)),  # Will get A♣
            sample_player_factory(PlayerId("p3"), Seat.SEAT_2, ChipAmount(1000)),  # Will get Q♠
        ]
        game = minimal_game_factory(players)

        deck = create_deck_with_top_cards(
            [
                Card(suit=Suit.SPADES, rank=Rank.KING),
                Card(suit=Suit.CLUBS, rank=Rank.ACE),  # Highest rank
                Card(suit=Suit.SPADES, rank=Rank.QUEEN),
            ]
        )

        # Act
        updated_game, _ = GameOrchestrator.initialize_game(game, deck)

        # Assert
        assert updated_game.button_seat == Seat.SEAT_1

    def test_two_is_lowest_card_in_high_card_draw(
        self,
        minimal_game_factory,
        sample_player_factory,
    ):
        """Two loses to all other ranks."""
        # Arrange
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)),  # Will get 2♠
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)),  # Will get 3♣
        ]
        game = minimal_game_factory(players)

        deck = create_deck_with_top_cards(
            [
                Card(suit=Suit.SPADES, rank=Rank.TWO),
                Card(suit=Suit.CLUBS, rank=Rank.THREE),  # Beats Two
            ]
        )

        # Act
        updated_game, _ = GameOrchestrator.initialize_game(game, deck)

        # Assert
        assert updated_game.button_seat == Seat.SEAT_1


class TestIsGameComplete:
    """
    Tests for tournament completion logic.

    Per RULE_BOOK Section 16.1: Tournament ends when one player has all chips.
    """

    def test_game_complete_with_one_player_remaining(
        self,
        minimal_game_factory,
        sample_player_factory,
    ):
        """Tournament is complete when only one active player remains."""
        # Arrange: 1 active player, 1 eliminated
        players = [
            sample_player_factory(
                PlayerId("p1"),
                Seat.SEAT_0,
                ChipAmount(6000),
                participation_status=HandParticipationStatus.IN_HAND,
            ),
            sample_player_factory(
                PlayerId("p2"),
                Seat.SEAT_1,
                ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
        ]
        game = minimal_game_factory(players)

        # Act
        is_complete = GameOrchestrator.is_game_complete(game)

        # Assert
        assert is_complete is True

    def test_game_complete_with_all_players_eliminated(
        self,
        minimal_game_factory,
        sample_player_factory,
    ):
        """Game is complete when all players are eliminated."""
        # Arrange: All players eliminated
        players = [
            sample_player_factory(
                PlayerId("p1"),
                Seat.SEAT_0,
                ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                PlayerId("p2"),
                Seat.SEAT_1,
                ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
        ]
        game = minimal_game_factory(players)

        # Act
        is_complete = GameOrchestrator.is_game_complete(game)

        # Assert: 0 active players means game is over
        assert is_complete is True

    def test_game_not_complete_with_two_players_remaining(
        self,
        minimal_game_factory,
        sample_player_factory,
    ):
        """Tournament continues with 2+ active players."""
        # Arrange: 2 players with chips
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)),
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)),
        ]
        game = minimal_game_factory(players)

        # Act
        is_complete = GameOrchestrator.is_game_complete(game)

        # Assert
        assert is_complete is False

    def test_game_not_complete_with_multiple_players_remaining(
        self,
        minimal_game_factory,
        sample_player_factory,
    ):
        """Tournament continues with multiple active players."""
        # Arrange: 4 players with chips
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(500)),
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1500)),
            sample_player_factory(PlayerId("p3"), Seat.SEAT_2, ChipAmount(2000)),
            sample_player_factory(PlayerId("p4"), Seat.SEAT_3, ChipAmount(1000)),
        ]
        game = minimal_game_factory(players)

        # Act
        is_complete = GameOrchestrator.is_game_complete(game)

        # Assert
        assert is_complete is False

    def test_game_complete_ignores_eliminated_players(
        self,
        minimal_game_factory,
        sample_player_factory,
    ):
        """Only counts active (non-eliminated) players."""
        # Arrange: 1 active player, 3 eliminated
        players = [
            sample_player_factory(
                PlayerId("p1"),
                Seat.SEAT_0,
                ChipAmount(6000),
                participation_status=HandParticipationStatus.IN_HAND,
            ),
            sample_player_factory(
                PlayerId("p2"),
                Seat.SEAT_1,
                ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                PlayerId("p3"),
                Seat.SEAT_2,
                ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                PlayerId("p4"),
                Seat.SEAT_3,
                ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
        ]
        game = minimal_game_factory(players)

        # Act
        is_complete = GameOrchestrator.is_game_complete(game)

        # Assert
        assert is_complete is True

    def test_game_not_complete_when_chips_are_unequal(
        self,
        minimal_game_factory,
        sample_player_factory,
    ):
        """Tournament continues even if chip counts are very unequal."""
        # Arrange: One player has most chips but not all
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(5900)),
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(100)),
        ]
        game = minimal_game_factory(players)

        # Act
        is_complete = GameOrchestrator.is_game_complete(game)

        # Assert: Still 2 active players
        assert is_complete is False

    def test_game_not_complete_when_short_stacks_remain(
        self,
        minimal_game_factory,
        sample_player_factory,
    ):
        """Tournament continues even with very short stacks (1 chip)."""
        # Arrange: Multiple players with minimal chips
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(5998)),
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1)),
            sample_player_factory(PlayerId("p3"), Seat.SEAT_2, ChipAmount(1)),
        ]
        game = minimal_game_factory(players)

        # Act
        is_complete = GameOrchestrator.is_game_complete(game)

        # Assert: 3 active players remain
        assert is_complete is False
