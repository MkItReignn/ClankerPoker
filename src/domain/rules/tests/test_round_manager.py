"""Behavioral tests for RoundManager.

Tests verify round progression and community card dealing according to RULE_BOOK.md:
- Advancing through betting rounds (PREFLOP → FLOP → TURN → RIVER)
- Resetting player and betting state for new rounds
- Dealing community cards with proper burn cards
- Pot calculation between rounds
- Position and action order recalculation
"""

from collections.abc import Callable
from dataclasses import replace

import pytest

from src.domain.models.card import Card, Rank, Suit
from src.domain.models.chips import ChipAmount
from src.domain.models.deck import Deck
from src.domain.models.game import Game, HandPhase, HandState
from src.domain.models.player import (
    BettingRoundActionStatus,
    HandParticipationStatus,
    Player,
)
from src.domain.models.players import Players
from src.domain.models.pot import Pot, PotState
from src.domain.models.seat import Seat
from src.domain.rules.round_manager import RoundManager


class TestRoundAdvancement:
    """Tests for advancing through betting rounds.

    RULE_BOOK.md Section 6: Betting Rounds
    - There are four betting rounds: PREFLOP, FLOP, TURN, RIVER
    - Each round must complete before advancing to the next
    """

    def test_advances_from_preflop_to_flop(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """After preflop betting completes, game advances to flop."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
                total_invested_this_hand=ChipAmount(100),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(900),
                total_invested_this_hand=ChipAmount(100),
            ),
        ]
        game = minimal_game_factory(
            players=Players.from_list(players),
        )

        assert game.hand_state.current_phase == HandPhase.PRE_FLOP

        advanced_game = RoundManager.advance(game)

        assert advanced_game.hand_state.current_phase == HandPhase.FLOP

    def test_advances_from_flop_to_turn(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """After flop betting completes, game advances to turn."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(900),
                total_invested_this_hand=ChipAmount(200),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(800),
                total_invested_this_hand=ChipAmount(200),
            ),
        ]
        game = minimal_game_factory(
            players=Players.from_list(players),
        )
        game = replace(
            game,
            hand_state=HandState(
                hand_number=1,
                current_phase=HandPhase.FLOP,
                community_cards=[
                    Card(rank=Rank.ACE, suit=Suit.SPADES),
                    Card(rank=Rank.KING, suit=Suit.HEARTS),
                    Card(rank=Rank.QUEEN, suit=Suit.DIAMONDS),
                ],
                is_initial_hand_setup=False,
            ),
        )

        assert game.hand_state.current_phase == HandPhase.FLOP

        advanced_game = RoundManager.advance(game)

        assert advanced_game.hand_state.current_phase == HandPhase.TURN

    def test_advances_from_turn_to_river(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """After turn betting completes, game advances to river."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(800),
                total_invested_this_hand=ChipAmount(300),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(700),
                total_invested_this_hand=ChipAmount(300),
            ),
        ]
        game = minimal_game_factory(
            players=Players.from_list(players),
        )
        game = replace(
            game,
            hand_state=HandState(
                hand_number=1,
                current_phase=HandPhase.TURN,
                community_cards=[
                    Card(rank=Rank.ACE, suit=Suit.SPADES),
                    Card(rank=Rank.KING, suit=Suit.HEARTS),
                    Card(rank=Rank.QUEEN, suit=Suit.DIAMONDS),
                    Card(rank=Rank.JACK, suit=Suit.CLUBS),
                ],
                is_initial_hand_setup=False,
            ),
        )

        assert game.hand_state.current_phase == HandPhase.TURN

        advanced_game = RoundManager.advance(game)

        assert advanced_game.hand_state.current_phase == HandPhase.RIVER

    def test_cannot_advance_from_river(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """River is the final betting round; cannot advance to showdown via RoundManager.

        Note: SHOWDOWN is not a betting round, so RoundManager.advance() should not
        be used to transition to showdown. The hand completer handles showdown logic.
        """
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(700),
                total_invested_this_hand=ChipAmount(400),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(600),
                total_invested_this_hand=ChipAmount(400),
            ),
        ]
        game = minimal_game_factory(
            players=Players.from_list(players),
        )
        game = replace(
            game,
            hand_state=HandState(
                hand_number=1,
                current_phase=HandPhase.RIVER,
                community_cards=[
                    Card(rank=Rank.ACE, suit=Suit.SPADES),
                    Card(rank=Rank.KING, suit=Suit.HEARTS),
                    Card(rank=Rank.QUEEN, suit=Suit.DIAMONDS),
                    Card(rank=Rank.JACK, suit=Suit.CLUBS),
                    Card(rank=Rank.TEN, suit=Suit.SPADES),
                ],
                is_initial_hand_setup=False,
            ),
        )

        assert game.hand_state.current_phase == HandPhase.RIVER

        # RoundManager should not advance from RIVER to SHOWDOWN
        # SHOWDOWN is handled by the hand completer, not RoundManager
        with pytest.raises(
            ValueError, match="Cannot advance beyond|No betting order rule"
        ):
            RoundManager.advance(game)

    def test_cannot_advance_beyond_showdown(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Showdown is the final phase; cannot advance further."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(700),
                total_invested_this_hand=ChipAmount(400),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(600),
                total_invested_this_hand=ChipAmount(400),
            ),
        ]
        game = minimal_game_factory(
            players=Players.from_list(players),
        )
        game = replace(
            game,
            hand_state=HandState(
                hand_number=1,
                current_phase=HandPhase.SHOWDOWN,
                community_cards=[
                    Card(rank=Rank.ACE, suit=Suit.SPADES),
                    Card(rank=Rank.KING, suit=Suit.HEARTS),
                    Card(rank=Rank.QUEEN, suit=Suit.DIAMONDS),
                    Card(rank=Rank.JACK, suit=Suit.CLUBS),
                    Card(rank=Rank.TEN, suit=Suit.SPADES),
                ],
                is_initial_hand_setup=False,
            ),
        )

        with pytest.raises(ValueError, match="Cannot advance beyond"):
            RoundManager.advance(game)

    def test_cannot_advance_with_no_players_in_hand(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Cannot advance if all players have folded."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
                participation_status=HandParticipationStatus.FOLDED,
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(900),
                participation_status=HandParticipationStatus.FOLDED,
            ),
        ]
        game = minimal_game_factory(
            players=Players.from_list(players),
        )

        with pytest.raises(
            ValueError,
            match="Cannot advance betting round: no players in hand",
        ):
            RoundManager.advance(game)


class TestPlayerStateResetBetweenRounds:
    """Tests that player state is properly reset when advancing to a new round.

    RULE_BOOK.md Section 6.1: The Four Betting Rounds
    - Each betting round is independent
    - Player bets reset at the start of each new round
    - Players need action again in the new round
    """

    def test_players_reset_for_new_round(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Players have their betting status reset when advancing rounds."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(900),
                total_invested_this_hand=ChipAmount(100),
                betting_status=BettingRoundActionStatus.ACTED,
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(900),
                total_invested_this_hand=ChipAmount(100),
                betting_status=BettingRoundActionStatus.ACTED,
            ),
        ]
        game = minimal_game_factory(
            players=Players.from_list(players),
        )

        advanced_game = RoundManager.advance(game)

        # All players should need action in the new round
        for player in advanced_game.players:
            assert (
                player.betting_status == BettingRoundActionStatus.NEEDS_ACTION
            )

    def test_players_maintain_chip_counts_between_rounds(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Player chip counts remain unchanged when advancing rounds."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(850),
                total_invested_this_hand=ChipAmount(150),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(750),
                total_invested_this_hand=ChipAmount(250),
            ),
        ]
        game = minimal_game_factory(
            players=Players.from_list(players),
        )

        advanced_game = RoundManager.advance(game)

        # Chip counts should be preserved
        p1 = advanced_game.players.get_by_id("p1")
        p2 = advanced_game.players.get_by_id("p2")
        assert p1 is not None
        assert p2 is not None
        assert p1.remaining_chips == ChipAmount(850)
        assert p2.remaining_chips == ChipAmount(750)
        # Total investment in hand should be preserved
        assert p1.total_invested_this_hand == ChipAmount(150)
        assert p2.total_invested_this_hand == ChipAmount(250)


class TestBettingStateResetBetweenRounds:
    """Tests that betting state is properly reset when advancing to a new round.

    RULE_BOOK.md Section 7.9.8: Postflop Specifics
    - Each new street resets player_current_bet to 0
    - round_current_bet resets to 0
    - First action: CHECK or BET available
    """

    def test_betting_state_reset_last_raise_increment(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Last raise increment resets to 0 when advancing to a new round."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(800),
                total_invested_this_hand=ChipAmount(200),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(800),
                total_invested_this_hand=ChipAmount(200),
            ),
        ]
        game = minimal_game_factory(
            players=Players.from_list(players),
            last_raise_increment=ChipAmount(100),
        )

        assert game.betting_state.last_raise_increment == ChipAmount(100)

        advanced_game = RoundManager.advance(game)

        assert advanced_game.betting_state.last_raise_increment == ChipAmount(
            0
        )

    def test_position_to_act_recalculated_for_new_round(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Position to act is recalculated based on new round's action order."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(900),
                total_invested_this_hand=ChipAmount(100),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(900),
                total_invested_this_hand=ChipAmount(100),
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(900),
                total_invested_this_hand=ChipAmount(100),
            ),
        ]
        game = minimal_game_factory(
            players=Players.from_list(players),
        )

        advanced_game = RoundManager.advance(game)

        # Position to act should be set (not NO_POSITION_TO_ACT)
        # The exact value depends on PositionManager logic
        assert advanced_game.betting_state.position_to_act >= 0


class TestPotCalculationBetweenRounds:
    """Tests that pot state is correctly calculated when advancing rounds.

    RULE_BOOK.md Section 9: All-In Situations and Side Pots
    - Pot is calculated after betting round completes
    - Side pots created when players are all-in for different amounts
    """

    def test_pot_calculated_when_advancing_rounds(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Pot state is recalculated when advancing to next round."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(800),
                total_invested_this_hand=ChipAmount(200),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(800),
                total_invested_this_hand=ChipAmount(200),
            ),
        ]
        game = minimal_game_factory(
            players=Players.from_list(players),
        )
        # Set a pot state with 0 chips to show it gets recalculated
        game = replace(
            game,
            pot_state=PotState(
                main_pot=Pot(
                    amount=ChipAmount(0),
                    eligible_player_ids=frozenset({"p1", "p2"}),
                ),
                side_pots=[],
            ),
        )

        advanced_game = RoundManager.advance(game)

        # Pot should be calculated (400 total from both players)
        assert advanced_game.pot_state.main_pot.amount == ChipAmount(400)


class TestCommunityCardsPreservedDuringAdvancement:
    """Tests that community cards are preserved when advancing rounds.

    RULE_BOOK.md Section 5.3: Community Card Deal
    - Community cards remain visible through all subsequent rounds
    - Cards dealt in flop stay visible through turn and river
    """

    def test_community_cards_preserved_when_advancing(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Community cards from previous rounds are preserved."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(900),
                total_invested_this_hand=ChipAmount(100),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(900),
                total_invested_this_hand=ChipAmount(100),
            ),
        ]
        game = minimal_game_factory(
            players=Players.from_list(players),
        )
        flop_cards = [
            Card(rank=Rank.ACE, suit=Suit.SPADES),
            Card(rank=Rank.KING, suit=Suit.HEARTS),
            Card(rank=Rank.QUEEN, suit=Suit.DIAMONDS),
        ]
        game = replace(
            game,
            hand_state=HandState(
                hand_number=1,
                current_phase=HandPhase.FLOP,
                community_cards=flop_cards,
                is_initial_hand_setup=False,
            ),
        )

        advanced_game = RoundManager.advance(game)

        # Flop cards should still be present after advancing to turn
        assert len(advanced_game.hand_state.community_cards) == 3
        assert advanced_game.hand_state.community_cards == flop_cards


class TestDealCommunityCardsValidation:
    """Tests validation rules for dealing community cards.

    RULE_BOOK.md Section 5.3: Community Card Deal
    - Preflop has no community cards
    - Flop deals 3 cards (total: 3)
    - Turn deals 1 card (total: 4)
    - River deals 1 card (total: 5)
    - Showdown has no additional cards
    """

    def test_cannot_deal_community_cards_on_preflop(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Cannot deal community cards during preflop phase."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
        ]
        game = minimal_game_factory(
            players=Players.from_list(players),
        )
        deck = Deck.create_shuffled(seed=42)

        assert game.hand_state.current_phase == HandPhase.PRE_FLOP

        with pytest.raises(
            ValueError,
            match="Cannot deal community cards: preflop has no community cards",
        ):
            RoundManager.deal_community_cards(game, deck)

    def test_cannot_deal_community_cards_on_showdown(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Cannot deal community cards during showdown phase."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(800),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(800),
            ),
        ]
        game = minimal_game_factory(
            players=Players.from_list(players),
        )
        game = replace(
            game,
            hand_state=HandState(
                hand_number=1,
                current_phase=HandPhase.SHOWDOWN,
                community_cards=[
                    Card(rank=Rank.ACE, suit=Suit.SPADES),
                    Card(rank=Rank.KING, suit=Suit.HEARTS),
                    Card(rank=Rank.QUEEN, suit=Suit.DIAMONDS),
                    Card(rank=Rank.JACK, suit=Suit.CLUBS),
                    Card(rank=Rank.TEN, suit=Suit.SPADES),
                ],
                is_initial_hand_setup=False,
            ),
        )
        deck = Deck.create_shuffled(seed=42)

        with pytest.raises(
            ValueError,
            match="Cannot deal community cards: already at showdown",
        ):
            RoundManager.deal_community_cards(game, deck)

    def test_cannot_deal_if_already_have_cards_for_current_phase(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Cannot deal community cards if already have the required cards for current phase."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(900),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(900),
            ),
        ]
        game = minimal_game_factory(
            players=Players.from_list(players),
        )
        # Set up game at FLOP with 3 community cards already dealt
        game = replace(
            game,
            hand_state=HandState(
                hand_number=1,
                current_phase=HandPhase.FLOP,
                community_cards=[
                    Card(rank=Rank.ACE, suit=Suit.SPADES),
                    Card(rank=Rank.KING, suit=Suit.HEARTS),
                    Card(rank=Rank.QUEEN, suit=Suit.DIAMONDS),
                ],
                is_initial_hand_setup=False,
            ),
        )
        deck = Deck.create_shuffled(seed=42)

        with pytest.raises(
            ValueError, match="Cannot deal community cards: already have"
        ):
            RoundManager.deal_community_cards(game, deck)


class TestDealFlopCards:
    """Tests dealing the flop (first 3 community cards).

    RULE_BOOK.md Section 5.3: Community Card Deal
    RULE_BOOK.md Section 5.4: Burn Cards
    - Burn 1 card
    - Deal 3 cards for flop
    - Total: 3 community cards visible
    """

    def test_deals_three_cards_for_flop(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Dealing flop adds 3 community cards to the board."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
        ]
        game = minimal_game_factory(
            players=Players.from_list(players),
        )
        # Set game to FLOP phase but with no community cards yet
        game = replace(
            game,
            hand_state=HandState(
                hand_number=1,
                current_phase=HandPhase.FLOP,
                community_cards=[],
                is_initial_hand_setup=False,
            ),
        )
        deck = Deck.create_shuffled(seed=42)
        initial_deck_size = deck.cards_remaining()

        updated_game, updated_deck = RoundManager.deal_community_cards(
            game, deck
        )

        assert len(updated_game.hand_state.community_cards) == 3
        # 4 cards consumed: 1 burn + 3 dealt
        assert updated_deck.cards_remaining() == initial_deck_size - 4

    def test_burns_card_before_dealing_flop(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """One card is burned before dealing the flop."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
        ]
        game = minimal_game_factory(
            players=Players.from_list(players),
        )
        game = replace(
            game,
            hand_state=HandState(
                hand_number=1,
                current_phase=HandPhase.FLOP,
                community_cards=[],
                is_initial_hand_setup=False,
            ),
        )
        deck = Deck.create_shuffled(seed=42)
        initial_cards = deck.cards_remaining()

        _, updated_deck = RoundManager.deal_community_cards(game, deck)

        # Total 4 cards consumed (1 burn + 3 flop cards)
        assert updated_deck.cards_remaining() == initial_cards - 4

    def test_flop_cards_are_added_to_game_state(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Flop cards are added to the game's community cards."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
        ]
        game = minimal_game_factory(
            players=Players.from_list(players),
        )
        game = replace(
            game,
            hand_state=HandState(
                hand_number=1,
                current_phase=HandPhase.FLOP,
                community_cards=[],
                is_initial_hand_setup=False,
            ),
        )
        deck = Deck.create_shuffled(seed=42)

        updated_game, _ = RoundManager.deal_community_cards(game, deck)

        # 3 flop cards should be present
        assert len(updated_game.hand_state.community_cards) == 3
        # All cards should be Card objects
        for card in updated_game.hand_state.community_cards:
            assert isinstance(card, Card)


class TestDealTurnCard:
    """Tests dealing the turn (4th community card).

    RULE_BOOK.md Section 5.3: Community Card Deal
    RULE_BOOK.md Section 5.4: Burn Cards
    - Burn 1 card
    - Deal 1 card for turn
    - Total: 4 community cards visible
    """

    def test_deals_one_card_for_turn(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Dealing turn adds 1 card to the existing 3 flop cards."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(900),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(900),
            ),
        ]
        game = minimal_game_factory(
            players=Players.from_list(players),
        )
        flop_cards = [
            Card(rank=Rank.ACE, suit=Suit.SPADES),
            Card(rank=Rank.KING, suit=Suit.HEARTS),
            Card(rank=Rank.QUEEN, suit=Suit.DIAMONDS),
        ]
        game = replace(
            game,
            hand_state=HandState(
                hand_number=1,
                current_phase=HandPhase.TURN,
                community_cards=flop_cards,
                is_initial_hand_setup=False,
            ),
        )
        deck = Deck.create_shuffled(seed=42)
        initial_deck_size = deck.cards_remaining()

        updated_game, updated_deck = RoundManager.deal_community_cards(
            game, deck
        )

        assert len(updated_game.hand_state.community_cards) == 4
        # 2 cards consumed: 1 burn + 1 turn
        assert updated_deck.cards_remaining() == initial_deck_size - 2

    def test_turn_preserves_existing_flop_cards(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Turn card is added to existing flop cards, not replacing them."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(900),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(900),
            ),
        ]
        game = minimal_game_factory(
            players=Players.from_list(players),
        )
        flop_cards = [
            Card(rank=Rank.ACE, suit=Suit.SPADES),
            Card(rank=Rank.KING, suit=Suit.HEARTS),
            Card(rank=Rank.QUEEN, suit=Suit.DIAMONDS),
        ]
        game = replace(
            game,
            hand_state=HandState(
                hand_number=1,
                current_phase=HandPhase.TURN,
                community_cards=flop_cards,
                is_initial_hand_setup=False,
            ),
        )
        deck = Deck.create_shuffled(seed=42)

        updated_game, _ = RoundManager.deal_community_cards(game, deck)

        # Original flop cards should still be present
        assert updated_game.hand_state.community_cards[0] == flop_cards[0]
        assert updated_game.hand_state.community_cards[1] == flop_cards[1]
        assert updated_game.hand_state.community_cards[2] == flop_cards[2]
        # Plus one new turn card
        assert len(updated_game.hand_state.community_cards) == 4


class TestDealRiverCard:
    """Tests dealing the river (5th and final community card).

    RULE_BOOK.md Section 5.3: Community Card Deal
    RULE_BOOK.md Section 5.4: Burn Cards
    - Burn 1 card
    - Deal 1 card for river
    - Total: 5 community cards visible
    """

    def test_deals_one_card_for_river(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Dealing river adds 1 card to the existing 4 cards."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(800),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(800),
            ),
        ]
        game = minimal_game_factory(
            players=Players.from_list(players),
        )
        turn_cards = [
            Card(rank=Rank.ACE, suit=Suit.SPADES),
            Card(rank=Rank.KING, suit=Suit.HEARTS),
            Card(rank=Rank.QUEEN, suit=Suit.DIAMONDS),
            Card(rank=Rank.JACK, suit=Suit.CLUBS),
        ]
        game = replace(
            game,
            hand_state=HandState(
                hand_number=1,
                current_phase=HandPhase.RIVER,
                community_cards=turn_cards,
                is_initial_hand_setup=False,
            ),
        )
        deck = Deck.create_shuffled(seed=42)
        initial_deck_size = deck.cards_remaining()

        updated_game, updated_deck = RoundManager.deal_community_cards(
            game, deck
        )

        assert len(updated_game.hand_state.community_cards) == 5
        # 2 cards consumed: 1 burn + 1 river
        assert updated_deck.cards_remaining() == initial_deck_size - 2

    def test_river_preserves_all_previous_cards(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """River card is added to all existing cards without replacing them."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(800),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(800),
            ),
        ]
        game = minimal_game_factory(
            players=Players.from_list(players),
        )
        turn_cards = [
            Card(rank=Rank.ACE, suit=Suit.SPADES),
            Card(rank=Rank.KING, suit=Suit.HEARTS),
            Card(rank=Rank.QUEEN, suit=Suit.DIAMONDS),
            Card(rank=Rank.JACK, suit=Suit.CLUBS),
        ]
        game = replace(
            game,
            hand_state=HandState(
                hand_number=1,
                current_phase=HandPhase.RIVER,
                community_cards=turn_cards,
                is_initial_hand_setup=False,
            ),
        )
        deck = Deck.create_shuffled(seed=42)

        updated_game, _ = RoundManager.deal_community_cards(game, deck)

        # All previous cards should still be present
        for i in range(4):
            assert updated_game.hand_state.community_cards[i] == turn_cards[i]
        # Plus one new river card
        assert len(updated_game.hand_state.community_cards) == 5

    def test_river_completes_the_board(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """After dealing river, exactly 5 community cards are visible."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(800),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(800),
            ),
        ]
        game = minimal_game_factory(
            players=Players.from_list(players),
        )
        turn_cards = [
            Card(rank=Rank.ACE, suit=Suit.SPADES),
            Card(rank=Rank.KING, suit=Suit.HEARTS),
            Card(rank=Rank.QUEEN, suit=Suit.DIAMONDS),
            Card(rank=Rank.JACK, suit=Suit.CLUBS),
        ]
        game = replace(
            game,
            hand_state=HandState(
                hand_number=1,
                current_phase=HandPhase.RIVER,
                community_cards=turn_cards,
                is_initial_hand_setup=False,
            ),
        )
        deck = Deck.create_shuffled(seed=42)

        updated_game, _ = RoundManager.deal_community_cards(game, deck)

        # Exactly 5 cards make up "the board"
        assert len(updated_game.hand_state.community_cards) == 5


class TestDeckMutation:
    """Tests that deck state is properly updated when dealing cards.

    RULE_BOOK.md Section 5.4: Burn Cards
    - Deck is mutated when burning and dealing cards
    - Burned cards are removed from play
    - Dealt cards are visible to all players
    """

    def test_deck_is_mutated_when_dealing_cards(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Dealing cards returns a new deck with updated state."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
        ]
        game = minimal_game_factory(
            players=Players.from_list(players),
        )
        game = replace(
            game,
            hand_state=HandState(
                hand_number=1,
                current_phase=HandPhase.FLOP,
                community_cards=[],
                is_initial_hand_setup=False,
            ),
        )
        original_deck = Deck.create_shuffled(seed=42)
        original_remaining = original_deck.cards_remaining()

        _, updated_deck = RoundManager.deal_community_cards(
            game, original_deck
        )

        # Updated deck should have fewer cards
        assert updated_deck.cards_remaining() < original_remaining
        # Original deck should be unchanged (immutability via deepcopy)
        assert original_deck.cards_remaining() == original_remaining

    def test_multiple_deal_operations_consume_correct_number_of_cards(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Dealing flop, turn, and river consumes correct total cards."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
        ]
        game = minimal_game_factory(
            players=Players.from_list(players),
        )
        deck = Deck.create_shuffled(seed=42)
        initial_cards = deck.cards_remaining()

        # Deal flop: burn 1 + deal 3 = 4 cards
        game_at_flop = replace(
            game,
            hand_state=HandState(
                hand_number=1,
                current_phase=HandPhase.FLOP,
                community_cards=[],
                is_initial_hand_setup=False,
            ),
        )
        game_after_flop, deck = RoundManager.deal_community_cards(
            game_at_flop, deck
        )
        assert deck.cards_remaining() == initial_cards - 4

        # Deal turn: burn 1 + deal 1 = 2 cards
        game_at_turn = replace(
            game_after_flop,
            hand_state=replace(
                game_after_flop.hand_state,
                current_phase=HandPhase.TURN,
            ),
        )
        game_after_turn, deck = RoundManager.deal_community_cards(
            game_at_turn, deck
        )
        assert deck.cards_remaining() == initial_cards - 6

        # Deal river: burn 1 + deal 1 = 2 cards
        game_at_river = replace(
            game_after_turn,
            hand_state=replace(
                game_after_turn.hand_state,
                current_phase=HandPhase.RIVER,
            ),
        )
        game_after_river, deck = RoundManager.deal_community_cards(
            game_at_river, deck
        )
        # Total: 4 + 2 + 2 = 8 cards consumed
        assert deck.cards_remaining() == initial_cards - 8

        # Final board should have 5 cards
        assert len(game_after_river.hand_state.community_cards) == 5
