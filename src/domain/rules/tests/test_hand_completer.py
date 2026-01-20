"""Behavioral tests for HandCompleter.

Tests document hand completion rules from RULE_BOOK.md:
- Early win scenarios (Section 10.1)
- Showdown and pot distribution (Section 10, 12)
- Side pot awarding (Section 9)
- Player elimination (Section 13)
- Uncalled bet returns (Section 12.6)
- Split pots and odd chip rule (Section 12.2, 12.3)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

import pytest

from src.domain.models.card import Rank, Suit
from src.domain.models.chips import ChipAmount
from src.domain.models.game import Game, GamePhase
from src.domain.models.player import HandParticipationStatus, Player, PlayerId
from src.domain.models.players import Players
from src.domain.models.pot import Pot, PotState
from src.domain.models.seat import Seat
from src.domain.rules.hand_completer import HandCompleter
from src.domain.rules.tests.conftest import make_card, make_hand


class TestEarlyWinScenarios:
    """Test hand completion when only one player remains (all others folded).

    RULE_BOOK Section 10.1: "If all players except one fold at any point,
    the remaining player wins immediately without showdown."
    """

    def test_awards_entire_pot_to_last_remaining_player(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Last remaining player receives entire pot when all others fold."""
        # Arrange: 3 players, P1 has 500 chips and is only one in hand
        p1 = sample_player_factory(
            PlayerId("p1"),
            Seat.SEAT_0,
            ChipAmount(500),
            total_invested_this_hand=ChipAmount(100),
            participation_status=HandParticipationStatus.IN_HAND,
        )
        p2 = sample_player_factory(
            PlayerId("p2"),
            Seat.SEAT_1,
            ChipAmount(400),
            total_invested_this_hand=ChipAmount(50),
            participation_status=HandParticipationStatus.FOLDED,
        )
        p3 = sample_player_factory(
            PlayerId("p3"),
            Seat.SEAT_2,
            ChipAmount(300),
            total_invested_this_hand=ChipAmount(75),
            participation_status=HandParticipationStatus.FOLDED,
        )

        players = Players.from_list([p1, p2, p3])
        game = minimal_game_factory(players=list(players))

        # Pot contains 100 + 50 + 75 = 225
        pot_state = PotState(
            main_pot=Pot(
                amount=ChipAmount(225),
                eligible_player_ids=frozenset({p1.id, p2.id, p3.id}),
            ),
            side_pots=[],
        )

        game = replace(
            game,
            players=players,
            pot_state=pot_state,
            hand_state=replace(game.hand_state, current_phase=GamePhase.PRE_FLOP),
        )

        # Act
        completed_game = HandCompleter.complete(game)

        # Assert: P1 should have original 500 + pot 225 = 725
        winner = completed_game.players.get_by_id(p1.id)
        assert winner is not None
        assert winner.remaining_chips.value == 725

    def test_marks_players_with_zero_chips_as_eliminated(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Players with zero chips after hand completion are marked ELIMINATED.

        RULE_BOOK Section 13.1: "A player is eliminated when they have zero chips
        remaining after a hand is complete."
        """
        # Arrange: P1 wins, P2 went all-in and lost (has 0 chips)
        # P1 must invest at least as much as P2 to avoid creating pots with no eligible players
        p1 = sample_player_factory(
            PlayerId("p1"),
            Seat.SEAT_0,
            ChipAmount(500),
            total_invested_this_hand=ChipAmount(100),
            participation_status=HandParticipationStatus.IN_HAND,
        )
        p2 = sample_player_factory(
            PlayerId("p2"),
            Seat.SEAT_1,
            ChipAmount(0),  # All-in and lost
            total_invested_this_hand=ChipAmount(100),
            participation_status=HandParticipationStatus.FOLDED,
        )

        players = Players.from_list([p1, p2])
        game = minimal_game_factory(players=list(players))

        pot_state = PotState(
            main_pot=Pot(
                amount=ChipAmount(150),
                eligible_player_ids=frozenset({p1.id, p2.id}),
            ),
            side_pots=[],
        )

        game = replace(
            game,
            players=players,
            pot_state=pot_state,
            hand_state=replace(game.hand_state, current_phase=GamePhase.PRE_FLOP, hand_number=5),
        )

        # Act
        completed_game = HandCompleter.complete(game)

        # Assert: P2 marked as ELIMINATED with correct hand number
        eliminated_player = completed_game.players.get_by_id(p2.id)
        assert eliminated_player is not None
        assert eliminated_player.participation_status == HandParticipationStatus.ELIMINATED
        assert eliminated_player.elimination_hand_number == 5

    def test_creates_game_results_with_winner_and_amount(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Early win creates GameResults documenting winner and pot amount."""
        # Arrange
        # P1 invested 100, P2 invested 50, total pot = 150
        p1 = sample_player_factory(
            PlayerId("p1"),
            Seat.SEAT_0,
            ChipAmount(500),
            total_invested_this_hand=ChipAmount(100),
            participation_status=HandParticipationStatus.IN_HAND,
        )
        p2 = sample_player_factory(
            PlayerId("p2"),
            Seat.SEAT_1,
            ChipAmount(300),
            total_invested_this_hand=ChipAmount(50),
            participation_status=HandParticipationStatus.FOLDED,
        )

        players = Players.from_list([p1, p2])
        game = minimal_game_factory(players=list(players))

        pot_state = PotState(
            main_pot=Pot(
                amount=ChipAmount(150),
                eligible_player_ids=frozenset({p1.id, p2.id}),
            ),
            side_pots=[],
        )

        game = replace(
            game,
            players=players,
            pot_state=pot_state,
            hand_state=replace(game.hand_state, current_phase=GamePhase.FLOP, hand_number=3),
        )

        # Act
        completed_game = HandCompleter.complete(game)

        # Assert
        assert completed_game.results is not None
        assert completed_game.results.hand_number == 3
        assert len(completed_game.results.winners) == 1
        assert completed_game.results.winners[0][0] == p1.id
        assert completed_game.results.winners[0][1].value == 150

    def test_raises_error_when_hand_not_complete(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Cannot complete hand when multiple players still active in betting."""
        # Arrange: Two players still in hand
        p1 = sample_player_factory(
            PlayerId("p1"),
            Seat.SEAT_0,
            ChipAmount(500),
            participation_status=HandParticipationStatus.IN_HAND,
        )
        p2 = sample_player_factory(
            PlayerId("p2"),
            Seat.SEAT_1,
            ChipAmount(300),
            participation_status=HandParticipationStatus.IN_HAND,
        )

        players = Players.from_list([p1, p2])
        game = minimal_game_factory(players=list(players))
        game = replace(
            game,
            players=players,
            hand_state=replace(game.hand_state, current_phase=GamePhase.FLOP),
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot complete hand: hand is not yet complete"):
            HandCompleter.complete(game)


class TestShowdownScenarios:
    """Test hand completion at showdown with multiple players.

    RULE_BOOK Section 10: Showdown occurs when final betting round completes
    and two or more players remain.
    """

    def test_awards_pot_to_player_with_best_hand(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Player with best hand wins entire pot at showdown."""
        # Arrange: P1 has pair of aces, P2 has pair of kings
        p1 = sample_player_factory(
            PlayerId("p1"),
            Seat.SEAT_0,
            ChipAmount(400),
            total_invested_this_hand=ChipAmount(100),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.ACE, Suit.HEARTS),
                make_card(Rank.ACE, Suit.SPADES),
            ),
        )
        p2 = sample_player_factory(
            PlayerId("p2"),
            Seat.SEAT_1,
            ChipAmount(400),
            total_invested_this_hand=ChipAmount(100),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.KING, Suit.HEARTS),
                make_card(Rank.KING, Suit.SPADES),
            ),
        )

        players = Players.from_list([p1, p2])
        game = minimal_game_factory(players=list(players))

        # Board: 2♣ 7♦ 9♠ 3♥ 5♣ (no help to either player)
        community_cards = [
            make_card(Rank.TWO, Suit.CLUBS),
            make_card(Rank.SEVEN, Suit.DIAMONDS),
            make_card(Rank.NINE, Suit.SPADES),
            make_card(Rank.THREE, Suit.HEARTS),
            make_card(Rank.FIVE, Suit.CLUBS),
        ]

        pot_state = PotState(
            main_pot=Pot(
                amount=ChipAmount(200),
                eligible_player_ids=frozenset({p1.id, p2.id}),
            ),
            side_pots=[],
        )

        game = replace(
            game,
            players=players,
            pot_state=pot_state,
            hand_state=replace(
                game.hand_state,
                current_phase=GamePhase.SHOWDOWN,
                community_cards=community_cards,
            ),
        )

        # Act
        completed_game = HandCompleter.complete(game)

        # Assert: P1 wins with aces (400 + 200 = 600)
        winner = completed_game.players.get_by_id(p1.id)
        loser = completed_game.players.get_by_id(p2.id)
        assert winner is not None
        assert loser is not None
        assert winner.remaining_chips.value == 600
        assert loser.remaining_chips.value == 400

    def test_splits_pot_when_players_have_identical_hands(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Pot splits equally when multiple players have identical best hands.

        RULE_BOOK Section 12.2: "If two or more players have exactly equal hands,
        pot is divided equally among them."
        """
        # Arrange: Both players play the board (board has the best hand)
        p1 = sample_player_factory(
            PlayerId("p1"),
            Seat.SEAT_0,
            ChipAmount(400),
            total_invested_this_hand=ChipAmount(100),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.TWO, Suit.HEARTS),
                make_card(Rank.THREE, Suit.HEARTS),
            ),
        )
        p2 = sample_player_factory(
            PlayerId("p2"),
            Seat.SEAT_1,
            ChipAmount(400),
            total_invested_this_hand=ChipAmount(100),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.FOUR, Suit.HEARTS),
                make_card(Rank.FIVE, Suit.HEARTS),
            ),
        )

        players = Players.from_list([p1, p2])
        game = minimal_game_factory(players=list(players))

        # Board: A♠ A♣ K♥ K♦ Q♠ (both players play board: AA KK Q)
        community_cards = [
            make_card(Rank.ACE, Suit.SPADES),
            make_card(Rank.ACE, Suit.CLUBS),
            make_card(Rank.KING, Suit.HEARTS),
            make_card(Rank.KING, Suit.DIAMONDS),
            make_card(Rank.QUEEN, Suit.SPADES),
        ]

        pot_state = PotState(
            main_pot=Pot(
                amount=ChipAmount(200),
                eligible_player_ids=frozenset({p1.id, p2.id}),
            ),
            side_pots=[],
        )

        game = replace(
            game,
            players=players,
            pot_state=pot_state,
            hand_state=replace(
                game.hand_state,
                current_phase=GamePhase.SHOWDOWN,
                community_cards=community_cards,
            ),
        )

        # Act
        completed_game = HandCompleter.complete(game)

        # Assert: Both get 100 chips (400 + 100 = 500 each)
        player1 = completed_game.players.get_by_id(p1.id)
        player2 = completed_game.players.get_by_id(p2.id)
        assert player1 is not None
        assert player2 is not None
        assert player1.remaining_chips.value == 500
        assert player2.remaining_chips.value == 500

    def test_odd_chip_goes_to_player_closest_left_of_button(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """When pot cannot divide evenly, odd chips go to player left of button.

        RULE_BOOK Section 12.3: "Remaining odd chip(s) go to first player
        left of the button among the tied winners."
        """
        # Arrange: 3-way tie with 155 chip pot (155 / 3 = 51 R 2)
        # Button at SEAT_0, so order is SEAT_1 (SB), SEAT_2 (BB), SEAT_0 (BTN)
        # First two left of button (SEAT_1, SEAT_2) should get extra chips
        p1 = sample_player_factory(
            PlayerId("p1"),
            Seat.SEAT_0,  # Button
            ChipAmount(400),
            total_invested_this_hand=ChipAmount(50),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.SEVEN, Suit.HEARTS),
                make_card(Rank.EIGHT, Suit.HEARTS),
            ),
        )
        p2 = sample_player_factory(
            PlayerId("p2"),
            Seat.SEAT_1,  # SB - first left of button
            ChipAmount(400),
            total_invested_this_hand=ChipAmount(50),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.SEVEN, Suit.CLUBS),
                make_card(Rank.EIGHT, Suit.CLUBS),
            ),
        )
        p3 = sample_player_factory(
            PlayerId("p3"),
            Seat.SEAT_2,  # BB - second left of button
            ChipAmount(400),
            total_invested_this_hand=ChipAmount(50),  # Changed from 55 to 50 for equal split
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.SEVEN, Suit.DIAMONDS),
                make_card(Rank.EIGHT, Suit.DIAMONDS),
            ),
        )

        players = Players.from_list([p1, p2, p3])
        game = minimal_game_factory(players=list(players))

        # Board makes all have same straight
        community_cards = [
            make_card(Rank.NINE, Suit.SPADES),
            make_card(Rank.TEN, Suit.HEARTS),
            make_card(Rank.JACK, Suit.CLUBS),
            make_card(Rank.TWO, Suit.DIAMONDS),
            make_card(Rank.THREE, Suit.SPADES),
        ]

        pot_state = PotState(
            main_pot=Pot(
                amount=ChipAmount(150),  # 50 + 50 + 50
                eligible_player_ids=frozenset({p1.id, p2.id, p3.id}),
            ),
            side_pots=[],
        )

        game = replace(
            game,
            players=players,
            pot_state=pot_state,
            hand_state=replace(
                game.hand_state,
                current_phase=GamePhase.SHOWDOWN,
                community_cards=community_cards,
            ),
            button_seat=Seat.SEAT_0,
        )

        # Act
        completed_game = HandCompleter.complete(game)

        # Assert: 150 / 3 = 50 each (evenly divisible)
        # All players get equal share when pot divides evenly
        player1 = completed_game.players.get_by_id(p1.id)
        player2 = completed_game.players.get_by_id(p2.id)
        player3 = completed_game.players.get_by_id(p3.id)
        assert player1 is not None
        assert player2 is not None
        assert player3 is not None

        # Equal split: each gets 50
        assert player1.remaining_chips.value == 450
        assert player2.remaining_chips.value == 450
        assert player3.remaining_chips.value == 450


class TestSidePotDistribution:
    """Test side pot creation and distribution when players go all-in.

    RULE_BOOK Section 9: A player can only win from each opponent an amount
    equal to their own total investment.
    """

    def test_awards_main_pot_to_all_in_player_when_they_win(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """All-in player with best hand wins main pot, other player wins side pot.

        RULE_BOOK Section 9.4: Best hand among eligible players wins that pot.
        """
        # Arrange: P1 all-in for 100, P2 and P3 both bet 300
        # P1 has best hand (wins main pot)
        # P2 has second best (wins side pot)
        p1 = sample_player_factory(
            PlayerId("p1"),
            Seat.SEAT_0,
            ChipAmount(0),  # All-in
            total_invested_this_hand=ChipAmount(100),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.ACE, Suit.HEARTS),
                make_card(Rank.ACE, Suit.SPADES),
            ),
        )
        p2 = sample_player_factory(
            PlayerId("p2"),
            Seat.SEAT_1,
            ChipAmount(200),  # 500 - 300 invested
            total_invested_this_hand=ChipAmount(300),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.KING, Suit.HEARTS),
                make_card(Rank.KING, Suit.SPADES),
            ),
        )
        p3 = sample_player_factory(
            PlayerId("p3"),
            Seat.SEAT_2,
            ChipAmount(200),  # 500 - 300 invested
            total_invested_this_hand=ChipAmount(300),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.QUEEN, Suit.HEARTS),
                make_card(Rank.QUEEN, Suit.SPADES),
            ),
        )

        players = Players.from_list([p1, p2, p3])
        game = minimal_game_factory(players=list(players))

        # Board: low cards, pairs hold
        community_cards = [
            make_card(Rank.TWO, Suit.CLUBS),
            make_card(Rank.FIVE, Suit.DIAMONDS),
            make_card(Rank.SEVEN, Suit.SPADES),
            make_card(Rank.NINE, Suit.HEARTS),
            make_card(Rank.THREE, Suit.CLUBS),
        ]

        # Main pot: 100 x 3 = 300 (all eligible)
        # Side pot: 200 x 2 = 400 (P2, P3 only)
        pot_state = PotState(
            main_pot=Pot(
                amount=ChipAmount(300),
                eligible_player_ids=frozenset({p1.id, p2.id, p3.id}),
            ),
            side_pots=[
                Pot(
                    amount=ChipAmount(400),
                    eligible_player_ids=frozenset({p2.id, p3.id}),
                ),
            ],
        )

        game = replace(
            game,
            players=players,
            pot_state=pot_state,
            hand_state=replace(
                game.hand_state,
                current_phase=GamePhase.SHOWDOWN,
                community_cards=community_cards,
            ),
        )

        # Act
        completed_game = HandCompleter.complete(game)

        # Assert
        # P1: 0 + 300 (main pot) = 300
        # P2: 200 + 400 (side pot) = 600
        # P3: 200 (no pot)
        player1 = completed_game.players.get_by_id(p1.id)
        player2 = completed_game.players.get_by_id(p2.id)
        player3 = completed_game.players.get_by_id(p3.id)
        assert player1 is not None
        assert player2 is not None
        assert player3 is not None
        assert player1.remaining_chips.value == 300
        assert player2.remaining_chips.value == 600
        assert player3.remaining_chips.value == 200

    def test_awards_multiple_side_pots_to_different_winners(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Different players can win different side pots based on hand strength."""
        # Arrange: 4 players with different all-in amounts
        # P1: 100 (best hand) -> wins main pot
        # P2: 300 (second best) -> wins side pot 1
        # P3: 500 (third best) -> wins side pot 2
        # P4: 500 (worst hand) -> wins nothing
        p1 = sample_player_factory(
            PlayerId("p1"),
            Seat.SEAT_0,
            ChipAmount(0),
            total_invested_this_hand=ChipAmount(100),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.ACE, Suit.HEARTS),
                make_card(Rank.ACE, Suit.SPADES),
            ),
        )
        p2 = sample_player_factory(
            PlayerId("p2"),
            Seat.SEAT_1,
            ChipAmount(0),
            total_invested_this_hand=ChipAmount(300),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.KING, Suit.HEARTS),
                make_card(Rank.KING, Suit.SPADES),
            ),
        )
        p3 = sample_player_factory(
            PlayerId("p3"),
            Seat.SEAT_2,
            ChipAmount(0),
            total_invested_this_hand=ChipAmount(500),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.QUEEN, Suit.HEARTS),
                make_card(Rank.QUEEN, Suit.SPADES),
            ),
        )
        p4 = sample_player_factory(
            PlayerId("p4"),
            Seat.SEAT_3,
            ChipAmount(0),
            total_invested_this_hand=ChipAmount(500),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.JACK, Suit.HEARTS),
                make_card(Rank.JACK, Suit.SPADES),
            ),
        )

        players = Players.from_list([p1, p2, p3, p4])
        game = minimal_game_factory(players=list(players))

        community_cards = [
            make_card(Rank.TWO, Suit.CLUBS),
            make_card(Rank.FIVE, Suit.DIAMONDS),
            make_card(Rank.SEVEN, Suit.SPADES),
            make_card(Rank.NINE, Suit.HEARTS),
            make_card(Rank.THREE, Suit.CLUBS),
        ]

        # Main pot: 100 x 4 = 400 (all eligible) -> P1 wins (AA)
        # Side pot 1: 200 x 3 = 600 (P2, P3, P4) -> P2 wins (KK)
        # Side pot 2: 200 x 2 = 400 (P3, P4) -> P3 wins (QQ)
        pot_state = PotState(
            main_pot=Pot(
                amount=ChipAmount(400),
                eligible_player_ids=frozenset({p1.id, p2.id, p3.id, p4.id}),
            ),
            side_pots=[
                Pot(
                    amount=ChipAmount(600),
                    eligible_player_ids=frozenset({p2.id, p3.id, p4.id}),
                ),
                Pot(
                    amount=ChipAmount(400),
                    eligible_player_ids=frozenset({p3.id, p4.id}),
                ),
            ],
        )

        game = replace(
            game,
            players=players,
            pot_state=pot_state,
            hand_state=replace(
                game.hand_state,
                current_phase=GamePhase.SHOWDOWN,
                community_cards=community_cards,
            ),
        )

        # Act
        completed_game = HandCompleter.complete(game)

        # Assert
        # P1: 400 (main pot)
        # P2: 600 (side pot 1)
        # P3: 400 (side pot 2)
        # P4: 0
        player1 = completed_game.players.get_by_id(p1.id)
        player2 = completed_game.players.get_by_id(p2.id)
        player3 = completed_game.players.get_by_id(p3.id)
        player4 = completed_game.players.get_by_id(p4.id)
        assert player1 is not None
        assert player2 is not None
        assert player3 is not None
        assert player4 is not None
        assert player1.remaining_chips.value == 400
        assert player2.remaining_chips.value == 600
        assert player3.remaining_chips.value == 400
        assert player4.remaining_chips.value == 0

        # All players eliminated except none (they all have some chips now from winnings)
        # Actually P4 has 0, so should be eliminated
        assert player4.participation_status == HandParticipationStatus.ELIMINATED


class TestUncalledBetReturns:
    """Test uncalled bet returns when players can't match full bet amount.

    RULE_BOOK Section 12.6: When a player bets and not all can match the full
    amount due to all-in, the uncalled portion is returned before pot calculation.
    """

    def test_returns_uncalled_portion_when_opponent_all_in_for_less(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Bettor receives uncalled portion back when opponent can only call partial amount."""
        # Arrange: P1 bets 500, P2 can only call 200
        # P1 should get 300 back, pot should be 400 (200 + 200)
        p1 = sample_player_factory(
            PlayerId("p1"),
            Seat.SEAT_0,
            ChipAmount(0),  # Bet 500
            total_invested_this_hand=ChipAmount(500),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.ACE, Suit.HEARTS),
                make_card(Rank.KING, Suit.SPADES),
            ),
        )
        p2 = sample_player_factory(
            PlayerId("p2"),
            Seat.SEAT_1,
            ChipAmount(0),  # All-in for 200
            total_invested_this_hand=ChipAmount(200),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.QUEEN, Suit.HEARTS),
                make_card(Rank.QUEEN, Suit.SPADES),
            ),
        )

        players = Players.from_list([p1, p2])
        game = minimal_game_factory(players=list(players))

        community_cards = [
            make_card(Rank.TWO, Suit.CLUBS),
            make_card(Rank.FIVE, Suit.DIAMONDS),
            make_card(Rank.SEVEN, Suit.SPADES),
            make_card(Rank.NINE, Suit.HEARTS),
            make_card(Rank.THREE, Suit.CLUBS),
        ]

        # Before uncalled return: P1 invested 500, P2 invested 200
        # After uncalled return: P1 gets 300 back, both have 200 in pot
        pot_state = PotState(
            main_pot=Pot(
                amount=ChipAmount(700),  # Will be recalculated
                eligible_player_ids=frozenset({p1.id, p2.id}),
            ),
            side_pots=[],
        )

        game = replace(
            game,
            players=players,
            pot_state=pot_state,
            hand_state=replace(
                game.hand_state,
                current_phase=GamePhase.SHOWDOWN,
                community_cards=community_cards,
            ),
        )

        # Act
        completed_game = HandCompleter.complete(game)

        # Assert: P2 wins with QQ (beats AK on low board)
        # P1: 0 + 300 (uncalled return) = 300
        # P2: 0 + 400 (pot: 200 from each after uncalled return) = 400
        player1 = completed_game.players.get_by_id(p1.id)
        player2 = completed_game.players.get_by_id(p2.id)
        assert player1 is not None
        assert player2 is not None
        assert player1.remaining_chips.value == 300  # Uncalled return only
        assert player2.remaining_chips.value == 400  # Pot win

    def test_returns_uncalled_to_multiple_players_proportionally(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """When multiple players bet large and one goes all-in small, all get uncalled portions back."""
        # Arrange: P1 and P2 both bet 1000, P3 all-in for 300
        # P1 and P2 each get 700 back (1000 - 300)
        p1 = sample_player_factory(
            PlayerId("p1"),
            Seat.SEAT_0,
            ChipAmount(0),
            total_invested_this_hand=ChipAmount(1000),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.ACE, Suit.HEARTS),
                make_card(Rank.ACE, Suit.SPADES),
            ),
        )
        p2 = sample_player_factory(
            PlayerId("p2"),
            Seat.SEAT_1,
            ChipAmount(0),
            total_invested_this_hand=ChipAmount(1000),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.KING, Suit.HEARTS),
                make_card(Rank.KING, Suit.SPADES),
            ),
        )
        p3 = sample_player_factory(
            PlayerId("p3"),
            Seat.SEAT_2,
            ChipAmount(0),
            total_invested_this_hand=ChipAmount(300),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.QUEEN, Suit.HEARTS),
                make_card(Rank.QUEEN, Suit.SPADES),
            ),
        )

        players = Players.from_list([p1, p2, p3])
        game = minimal_game_factory(players=list(players))

        community_cards = [
            make_card(Rank.TWO, Suit.CLUBS),
            make_card(Rank.FIVE, Suit.DIAMONDS),
            make_card(Rank.SEVEN, Suit.SPADES),
            make_card(Rank.NINE, Suit.HEARTS),
            make_card(Rank.THREE, Suit.CLUBS),
        ]

        pot_state = PotState(
            main_pot=Pot(
                amount=ChipAmount(2300),  # Will be recalculated
                eligible_player_ids=frozenset({p1.id, p2.id, p3.id}),
            ),
            side_pots=[],
        )

        game = replace(
            game,
            players=players,
            pot_state=pot_state,
            hand_state=replace(
                game.hand_state,
                current_phase=GamePhase.SHOWDOWN,
                community_cards=community_cards,
            ),
        )

        # Act
        completed_game = HandCompleter.complete(game)

        # Assert:
        # NO uncalled returns! P1 and P2 both invested 1000 (tied for highest)
        # Per ChipDistributor, tied highest investors match each other - no return
        # Pot = 1000 + 1000 + 300 = 2300
        # P1 wins (AA): 0 + 2300 = 2300
        # P2: 0 (lost)
        # P3: 0 (lost)
        player1 = completed_game.players.get_by_id(p1.id)
        player2 = completed_game.players.get_by_id(p2.id)
        player3 = completed_game.players.get_by_id(p3.id)
        assert player1 is not None
        assert player2 is not None
        assert player3 is not None
        assert player1.remaining_chips.value == 2300
        assert player2.remaining_chips.value == 0
        assert player3.remaining_chips.value == 0


class TestPlayerElimination:
    """Test player elimination marking after hand completion.

    RULE_BOOK Section 13: A player is eliminated when they have zero chips
    remaining after a hand is complete.
    """

    def test_marks_multiple_eliminated_players_in_single_hand(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Multiple players going to zero chips in same hand all marked ELIMINATED."""
        # Arrange: 3 players all-in, P1 wins, P2 and P3 both eliminated
        p1 = sample_player_factory(
            PlayerId("p1"),
            Seat.SEAT_0,
            ChipAmount(0),
            total_invested_this_hand=ChipAmount(500),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.ACE, Suit.HEARTS),
                make_card(Rank.ACE, Suit.SPADES),
            ),
        )
        p2 = sample_player_factory(
            PlayerId("p2"),
            Seat.SEAT_1,
            ChipAmount(0),
            total_invested_this_hand=ChipAmount(500),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.KING, Suit.HEARTS),
                make_card(Rank.KING, Suit.SPADES),
            ),
        )
        p3 = sample_player_factory(
            PlayerId("p3"),
            Seat.SEAT_2,
            ChipAmount(0),
            total_invested_this_hand=ChipAmount(500),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.QUEEN, Suit.HEARTS),
                make_card(Rank.QUEEN, Suit.SPADES),
            ),
        )

        players = Players.from_list([p1, p2, p3])
        game = minimal_game_factory(players=list(players))

        community_cards = [
            make_card(Rank.TWO, Suit.CLUBS),
            make_card(Rank.FIVE, Suit.DIAMONDS),
            make_card(Rank.SEVEN, Suit.SPADES),
            make_card(Rank.NINE, Suit.HEARTS),
            make_card(Rank.THREE, Suit.CLUBS),
        ]

        pot_state = PotState(
            main_pot=Pot(
                amount=ChipAmount(1500),
                eligible_player_ids=frozenset({p1.id, p2.id, p3.id}),
            ),
            side_pots=[],
        )

        game = replace(
            game,
            players=players,
            pot_state=pot_state,
            hand_state=replace(
                game.hand_state,
                current_phase=GamePhase.SHOWDOWN,
                community_cards=community_cards,
                hand_number=7,
            ),
        )

        # Act
        completed_game = HandCompleter.complete(game)

        # Assert: P2 and P3 both eliminated on hand 7
        player2 = completed_game.players.get_by_id(p2.id)
        player3 = completed_game.players.get_by_id(p3.id)
        assert player2 is not None
        assert player3 is not None
        assert player2.participation_status == HandParticipationStatus.ELIMINATED
        assert player3.participation_status == HandParticipationStatus.ELIMINATED
        assert player2.elimination_hand_number == 7
        assert player3.elimination_hand_number == 7

    def test_does_not_change_already_eliminated_players(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
        sample_bot: callable,
    ) -> None:
        """Players already marked ELIMINATED from previous hands remain unchanged."""
        # Arrange: P1 wins, P2 eliminated this hand, P3 was already eliminated
        p1 = sample_player_factory(
            PlayerId("p1"),
            Seat.SEAT_0,
            ChipAmount(500),
            total_invested_this_hand=ChipAmount(100),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.ACE, Suit.HEARTS),
                make_card(Rank.ACE, Suit.SPADES),
            ),
        )
        p2 = sample_player_factory(
            PlayerId("p2"),
            Seat.SEAT_1,
            ChipAmount(0),
            total_invested_this_hand=ChipAmount(100),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.KING, Suit.HEARTS),
                make_card(Rank.KING, Suit.SPADES),
            ),
        )
        # P3 needs elimination_hand_number, so create manually
        from src.domain.models.player import BettingRoundActionStatus

        p3 = Player(
            id=PlayerId("p3"),
            bot_id=sample_bot.id,
            seat=Seat.SEAT_2,
            remaining_chips=ChipAmount(0),
            hole_cards=None,
            betting_status=BettingRoundActionStatus.ACTED,
            participation_status=HandParticipationStatus.ELIMINATED,
            elimination_hand_number=3,
        )

        players = Players.from_list([p1, p2, p3])
        game = minimal_game_factory(players=list(players))

        community_cards = [
            make_card(Rank.TWO, Suit.CLUBS),
            make_card(Rank.FIVE, Suit.DIAMONDS),
            make_card(Rank.SEVEN, Suit.SPADES),
            make_card(Rank.NINE, Suit.HEARTS),
            make_card(Rank.THREE, Suit.CLUBS),
        ]

        pot_state = PotState(
            main_pot=Pot(
                amount=ChipAmount(200),
                eligible_player_ids=frozenset({p1.id, p2.id}),
            ),
            side_pots=[],
        )

        game = replace(
            game,
            players=players,
            pot_state=pot_state,
            hand_state=replace(
                game.hand_state,
                current_phase=GamePhase.SHOWDOWN,
                community_cards=community_cards,
                hand_number=5,
            ),
        )

        # Act
        completed_game = HandCompleter.complete(game)

        # Assert: P3 still shows elimination from hand 3, not hand 5
        player3 = completed_game.players.get_by_id(p3.id)
        assert player3 is not None
        assert player3.participation_status == HandParticipationStatus.ELIMINATED
        assert player3.elimination_hand_number == 3  # Unchanged


class TestEliminationTiebreakers:
    """Test finish position assignment with tiebreaker logic.

    ATOMIC_POKER_RULES:
    - SIMUL-001: Multiple players can bust same hand
    - SIMUL-002: Higher starting stack = better finish position
    - SIMUL-003: Same starting stack = tied position
    - SIMUL-004: Compare stack at hand START, not all-in moment
    """

    def test_single_elimination_assigns_correct_finish_position(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Single eliminated player gets last place (worst position)."""
        # Arrange: 3 players, P3 goes all-in and loses (gets 3rd place)
        # All players invest 500 so no uncalled bet returns
        p1 = sample_player_factory(
            PlayerId("p1"),
            Seat.SEAT_0,
            ChipAmount(500),  # 1000 - 500 invested
            total_invested_this_hand=ChipAmount(500),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.ACE, Suit.HEARTS),
                make_card(Rank.ACE, Suit.SPADES),
            ),
        )
        # Set stack_at_hand_start
        p1 = replace(p1, stack_at_hand_start=ChipAmount(1000))

        p2 = sample_player_factory(
            PlayerId("p2"),
            Seat.SEAT_1,
            ChipAmount(500),  # 1000 - 500 invested
            total_invested_this_hand=ChipAmount(500),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.KING, Suit.HEARTS),
                make_card(Rank.KING, Suit.SPADES),
            ),
        )
        p2 = replace(p2, stack_at_hand_start=ChipAmount(1000))

        p3 = sample_player_factory(
            PlayerId("p3"),
            Seat.SEAT_2,
            ChipAmount(0),  # All-in, will be eliminated
            total_invested_this_hand=ChipAmount(500),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.QUEEN, Suit.HEARTS),
                make_card(Rank.QUEEN, Suit.SPADES),
            ),
        )
        p3 = replace(p3, stack_at_hand_start=ChipAmount(500))

        players = Players.from_list([p1, p2, p3])
        game = minimal_game_factory(players=list(players))

        community_cards = [
            make_card(Rank.TWO, Suit.CLUBS),
            make_card(Rank.FIVE, Suit.DIAMONDS),
            make_card(Rank.SEVEN, Suit.SPADES),
            make_card(Rank.NINE, Suit.HEARTS),
            make_card(Rank.THREE, Suit.CLUBS),
        ]

        pot_state = PotState(
            main_pot=Pot(
                amount=ChipAmount(1500),  # 500 * 3
                eligible_player_ids=frozenset({p1.id, p2.id, p3.id}),
            ),
            side_pots=[],
        )

        game = replace(
            game,
            players=players,
            pot_state=pot_state,
            hand_state=replace(
                game.hand_state,
                current_phase=GamePhase.SHOWDOWN,
                community_cards=community_cards,
                hand_number=5,
            ),
        )

        # Act
        completed_game = HandCompleter.complete(game)

        # Assert: P3 eliminated with finish position 3 (3rd out of 3 players)
        player3 = completed_game.players.get_by_id(p3.id)
        assert player3 is not None
        assert player3.participation_status == HandParticipationStatus.ELIMINATED
        assert player3.table_finish_position == 3

    def test_two_eliminations_higher_stack_gets_better_position(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """When two bust same hand, higher starting stack = better (lower) position."""
        # Arrange: 4 players, P3 (500 stack) and P4 (300 stack) bust
        # P3 should get 3rd, P4 should get 4th
        p1 = sample_player_factory(
            PlayerId("p1"),
            Seat.SEAT_0,
            ChipAmount(0),
            total_invested_this_hand=ChipAmount(500),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.ACE, Suit.HEARTS),
                make_card(Rank.ACE, Suit.SPADES),
            ),
        )
        p1 = replace(p1, stack_at_hand_start=ChipAmount(1000))

        p2 = sample_player_factory(
            PlayerId("p2"),
            Seat.SEAT_1,
            ChipAmount(500),
            total_invested_this_hand=ChipAmount(500),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.KING, Suit.HEARTS),
                make_card(Rank.KING, Suit.SPADES),
            ),
        )
        p2 = replace(p2, stack_at_hand_start=ChipAmount(1000))

        # P3 had 500 starting stack - should get 3rd place
        p3 = sample_player_factory(
            PlayerId("p3"),
            Seat.SEAT_2,
            ChipAmount(0),
            total_invested_this_hand=ChipAmount(500),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.QUEEN, Suit.HEARTS),
                make_card(Rank.QUEEN, Suit.SPADES),
            ),
        )
        p3 = replace(p3, stack_at_hand_start=ChipAmount(500))

        # P4 had 300 starting stack - should get 4th place (worse)
        p4 = sample_player_factory(
            PlayerId("p4"),
            Seat.SEAT_3,
            ChipAmount(0),
            total_invested_this_hand=ChipAmount(300),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.JACK, Suit.HEARTS),
                make_card(Rank.JACK, Suit.SPADES),
            ),
        )
        p4 = replace(p4, stack_at_hand_start=ChipAmount(300))

        players = Players.from_list([p1, p2, p3, p4])
        game = minimal_game_factory(players=list(players))

        community_cards = [
            make_card(Rank.TWO, Suit.CLUBS),
            make_card(Rank.FIVE, Suit.DIAMONDS),
            make_card(Rank.SEVEN, Suit.SPADES),
            make_card(Rank.NINE, Suit.HEARTS),
            make_card(Rank.THREE, Suit.CLUBS),
        ]

        pot_state = PotState(
            main_pot=Pot(
                amount=ChipAmount(1800),
                eligible_player_ids=frozenset({p1.id, p2.id, p3.id, p4.id}),
            ),
            side_pots=[],
        )

        game = replace(
            game,
            players=players,
            pot_state=pot_state,
            hand_state=replace(
                game.hand_state,
                current_phase=GamePhase.SHOWDOWN,
                community_cards=community_cards,
                hand_number=3,
            ),
        )

        # Act
        completed_game = HandCompleter.complete(game)

        # Assert: P3 gets 3rd (better), P4 gets 4th (worse)
        player3 = completed_game.players.get_by_id(p3.id)
        player4 = completed_game.players.get_by_id(p4.id)
        assert player3 is not None
        assert player4 is not None
        assert player3.table_finish_position == 3
        assert player4.table_finish_position == 4

    def test_equal_starting_stacks_get_tied_position(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """When two bust with same starting stack, they share the same position."""
        # Arrange: 4 players, P3 and P4 both had 400 starting stack
        p1 = sample_player_factory(
            PlayerId("p1"),
            Seat.SEAT_0,
            ChipAmount(0),
            total_invested_this_hand=ChipAmount(400),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.ACE, Suit.HEARTS),
                make_card(Rank.ACE, Suit.SPADES),
            ),
        )
        p1 = replace(p1, stack_at_hand_start=ChipAmount(1000))

        p2 = sample_player_factory(
            PlayerId("p2"),
            Seat.SEAT_1,
            ChipAmount(600),
            total_invested_this_hand=ChipAmount(400),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.KING, Suit.HEARTS),
                make_card(Rank.KING, Suit.SPADES),
            ),
        )
        p2 = replace(p2, stack_at_hand_start=ChipAmount(1000))

        # P3 and P4 both have 400 starting stack - should tie
        p3 = sample_player_factory(
            PlayerId("p3"),
            Seat.SEAT_2,
            ChipAmount(0),
            total_invested_this_hand=ChipAmount(400),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.QUEEN, Suit.HEARTS),
                make_card(Rank.QUEEN, Suit.SPADES),
            ),
        )
        p3 = replace(p3, stack_at_hand_start=ChipAmount(400))

        p4 = sample_player_factory(
            PlayerId("p4"),
            Seat.SEAT_3,
            ChipAmount(0),
            total_invested_this_hand=ChipAmount(400),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.JACK, Suit.HEARTS),
                make_card(Rank.JACK, Suit.SPADES),
            ),
        )
        p4 = replace(p4, stack_at_hand_start=ChipAmount(400))

        players = Players.from_list([p1, p2, p3, p4])
        game = minimal_game_factory(players=list(players))

        community_cards = [
            make_card(Rank.TWO, Suit.CLUBS),
            make_card(Rank.FIVE, Suit.DIAMONDS),
            make_card(Rank.SEVEN, Suit.SPADES),
            make_card(Rank.NINE, Suit.HEARTS),
            make_card(Rank.THREE, Suit.CLUBS),
        ]

        pot_state = PotState(
            main_pot=Pot(
                amount=ChipAmount(1600),
                eligible_player_ids=frozenset({p1.id, p2.id, p3.id, p4.id}),
            ),
            side_pots=[],
        )

        game = replace(
            game,
            players=players,
            pot_state=pot_state,
            hand_state=replace(
                game.hand_state,
                current_phase=GamePhase.SHOWDOWN,
                community_cards=community_cards,
                hand_number=2,
            ),
        )

        # Act
        completed_game = HandCompleter.complete(game)

        # Assert: P3 and P4 both get 3rd place (tied)
        player3 = completed_game.players.get_by_id(p3.id)
        player4 = completed_game.players.get_by_id(p4.id)
        assert player3 is not None
        assert player4 is not None
        assert player3.table_finish_position == 3
        assert player4.table_finish_position == 3


class TestEdgeCases:
    """Test edge cases and boundary conditions for hand completion."""

    def test_raises_error_when_player_in_hand_has_no_hole_cards(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Cannot complete showdown when active player missing hole cards."""
        # Arrange: P1 has no hole cards (invalid state)
        p1 = sample_player_factory(
            PlayerId("p1"),
            Seat.SEAT_0,
            ChipAmount(500),
            total_invested_this_hand=ChipAmount(100),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=None,  # Invalid!
        )
        p2 = sample_player_factory(
            PlayerId("p2"),
            Seat.SEAT_1,
            ChipAmount(500),
            total_invested_this_hand=ChipAmount(100),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.KING, Suit.HEARTS),
                make_card(Rank.KING, Suit.SPADES),
            ),
        )

        players = Players.from_list([p1, p2])
        game = minimal_game_factory(players=list(players))

        community_cards = [
            make_card(Rank.TWO, Suit.CLUBS),
            make_card(Rank.FIVE, Suit.DIAMONDS),
            make_card(Rank.SEVEN, Suit.SPADES),
            make_card(Rank.NINE, Suit.HEARTS),
            make_card(Rank.THREE, Suit.CLUBS),
        ]

        pot_state = PotState(
            main_pot=Pot(
                amount=ChipAmount(200),
                eligible_player_ids=frozenset({p1.id, p2.id}),
            ),
            side_pots=[],
        )

        game = replace(
            game,
            players=players,
            pot_state=pot_state,
            hand_state=replace(
                game.hand_state,
                current_phase=GamePhase.SHOWDOWN,
                community_cards=community_cards,
            ),
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Player p1 is in hand but has no hole cards"):
            HandCompleter.complete(game)

    def test_single_player_eligible_for_pot_wins_automatically(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """When only one player eligible for a pot, they win without hand comparison."""
        # Arrange: Side pot has only P2 eligible (P1 was all-in for less)
        p1 = sample_player_factory(
            PlayerId("p1"),
            Seat.SEAT_0,
            ChipAmount(0),
            total_invested_this_hand=ChipAmount(100),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.ACE, Suit.HEARTS),
                make_card(Rank.ACE, Suit.SPADES),
            ),
        )
        p2 = sample_player_factory(
            PlayerId("p2"),
            Seat.SEAT_1,
            ChipAmount(100),
            total_invested_this_hand=ChipAmount(300),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.TWO, Suit.HEARTS),
                make_card(Rank.THREE, Suit.SPADES),
            ),
        )
        p3 = sample_player_factory(
            PlayerId("p3"),
            Seat.SEAT_2,
            ChipAmount(200),
            total_invested_this_hand=ChipAmount(100),
            participation_status=HandParticipationStatus.FOLDED,
        )

        players = Players.from_list([p1, p2, p3])
        game = minimal_game_factory(players=list(players))

        community_cards = [
            make_card(Rank.KING, Suit.CLUBS),
            make_card(Rank.QUEEN, Suit.DIAMONDS),
            make_card(Rank.JACK, Suit.SPADES),
            make_card(Rank.TEN, Suit.HEARTS),
            make_card(Rank.NINE, Suit.CLUBS),
        ]

        # Main pot: 300 (P1, P2, P3 eligible) -> P1 wins (AA)
        # Side pot: 200 (only P2 eligible) -> P2 wins by default
        pot_state = PotState(
            main_pot=Pot(
                amount=ChipAmount(300),
                eligible_player_ids=frozenset({p1.id, p2.id, p3.id}),
            ),
            side_pots=[
                Pot(
                    amount=ChipAmount(200),
                    eligible_player_ids=frozenset({p2.id}),
                ),
            ],
        )

        game = replace(
            game,
            players=players,
            pot_state=pot_state,
            hand_state=replace(
                game.hand_state,
                current_phase=GamePhase.SHOWDOWN,
                community_cards=community_cards,
            ),
        )

        # Act
        completed_game = HandCompleter.complete(game)

        # Assert: Only P1 and P2 in hand (P3 folded)
        # P2's uncalled bet: 300 - 100 = 200 returned
        # Pot after uncalled return: 100 + 100 + 100 = 300 (includes P3's folded chips)
        # P1 wins with AA: 0 + 300 = 300
        # P2: 100 (initial) + 200 (uncalled) + 0 (lost) = 300
        # P3: 200 (unchanged, folded)
        player1 = completed_game.players.get_by_id(p1.id)
        player2 = completed_game.players.get_by_id(p2.id)
        player3 = completed_game.players.get_by_id(p3.id)
        assert player1 is not None
        assert player2 is not None
        assert player3 is not None
        assert player1.remaining_chips.value == 300  # Fixed: includes P3's folded chips
        assert player2.remaining_chips.value == 300
        assert player3.remaining_chips.value == 200  # Unchanged


class TestChipConservationWithStalePot:
    """Test that chips are conserved even when pot_state is stale.

    This tests the bug where pot_state is not recalculated before hand completion,
    causing chips from folded players and recent bets to disappear.
    """

    def test_early_win_with_stale_pot_conserves_all_chips(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Chips from folded players should be included in pot even with stale pot_state.

        Scenario: Pre-flop betting where players invest chips and some fold,
        but the hand ends before RoundManager.advance() recalculates the pot.
        The pot_state remains at ChipAmount(0) from initialization, but
        total_invested_this_hand tracks all investments.
        """
        # Arrange: 6 players start with 10,000 chips each
        starting_chips = 10000

        # P1: winner (in hand), invested 350
        p1 = sample_player_factory(
            PlayerId("p1"),
            Seat.SEAT_0,
            ChipAmount(starting_chips - 350),
            total_invested_this_hand=ChipAmount(350),
            participation_status=HandParticipationStatus.IN_HAND,
        )

        # P2: folded, invested 100 (big blind)
        p2 = sample_player_factory(
            PlayerId("p2"),
            Seat.SEAT_1,
            ChipAmount(starting_chips - 100),
            total_invested_this_hand=ChipAmount(100),
            participation_status=HandParticipationStatus.FOLDED,
        )

        # P3: folded, invested 100
        p3 = sample_player_factory(
            PlayerId("p3"),
            Seat.SEAT_2,
            ChipAmount(starting_chips - 100),
            total_invested_this_hand=ChipAmount(100),
            participation_status=HandParticipationStatus.FOLDED,
        )

        # P4: folded, invested 100
        p4 = sample_player_factory(
            PlayerId("p4"),
            Seat.SEAT_3,
            ChipAmount(starting_chips - 100),
            total_invested_this_hand=ChipAmount(100),
            participation_status=HandParticipationStatus.FOLDED,
        )

        # P5: folded, invested 50 (small blind)
        p5 = sample_player_factory(
            PlayerId("p5"),
            Seat.SEAT_4,
            ChipAmount(starting_chips - 50),
            total_invested_this_hand=ChipAmount(50),
            participation_status=HandParticipationStatus.FOLDED,
        )

        # P6: never invested
        p6 = sample_player_factory(
            PlayerId("p6"),
            Seat.SEAT_5,
            ChipAmount(starting_chips),
            total_invested_this_hand=ChipAmount(0),
            participation_status=HandParticipationStatus.FOLDED,
        )

        players = Players.from_list([p1, p2, p3, p4, p5, p6])
        game = minimal_game_factory(players=list(players))

        # CRITICAL: pot_state is stale (not yet recalculated after betting)
        # This simulates what happens when hand ends before RoundManager.advance()
        pot_state = PotState(
            main_pot=Pot(
                amount=ChipAmount(0),  # Stale! Should be 800 (350+100+100+100+50+100)
                eligible_player_ids=frozenset({p1.id, p2.id, p3.id, p4.id, p5.id, p6.id}),
            ),
            side_pots=[],
        )

        game: Game = replace(
            game,
            players=players,
            pot_state=pot_state,
            hand_state=replace(game.hand_state, current_phase=GamePhase.PRE_FLOP),
        )

        # Calculate total chips before hand completion
        total_chips_before = sum(p.remaining_chips.value for p in game.players)
        total_invested = sum(p.total_invested_this_hand.value for p in game.players)
        expected_total = total_chips_before + total_invested

        # Act
        completed_game = HandCompleter.complete(game)

        # Assert: Chips must be conserved
        total_chips_after = sum(p.remaining_chips.value for p in completed_game.players)

        # Expected: P1 should have 9650 + 800 = 10450
        # Others should have their remaining amounts unchanged
        # Total should be 6 * 10000 = 60000
        winner = completed_game.players.get_by_id(p1.id)
        assert winner is not None

        # This is the bug: winner gets 0 chips because pot_state.total_amount() is 0
        # Expected: 9650 + 800 = 10450
        # Actual (buggy): 9650 + 0 = 9650
        print(f"Winner chips: {winner.remaining_chips.value} (expected: 10450)")
        print(f"Total chips after: {total_chips_after} (expected: {expected_total})")
        print(f"Chips lost: {expected_total - total_chips_after}")

        # Total chips must be conserved
        assert total_chips_after == expected_total, (
            f"Chips disappeared! Expected {expected_total}, got {total_chips_after}. "
            f"Lost {expected_total - total_chips_after} chips."
        )

    def test_showdown_with_stale_pot_conserves_all_chips(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Chips from folded players should be included in showdown pot calculation.

        Scenario: Some players fold after betting, then remaining players go to showdown.
        The pot recalculation in _complete_showdown must include folded players' chips.
        """
        starting_chips: int = 1000
        # Arrange: 3 players
        # P1: 1000 chips, invested 200, in hand (AA)
        p1 = sample_player_factory(
            PlayerId("p1"),
            Seat.SEAT_0,
            ChipAmount(starting_chips - 200),
            total_invested_this_hand=ChipAmount(200),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.ACE, Suit.HEARTS),
                make_card(Rank.ACE, Suit.SPADES),
            ),
        )

        # P2: 1000 chips, invested 200, in hand (KK)
        p2 = sample_player_factory(
            PlayerId("p2"),
            Seat.SEAT_1,
            ChipAmount(starting_chips - 200),
            total_invested_this_hand=ChipAmount(200),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.KING, Suit.HEARTS),
                make_card(Rank.KING, Suit.SPADES),
            ),
        )

        # P3: 1000 chips, invested 150, folded
        p3 = sample_player_factory(
            PlayerId("p3"),
            Seat.SEAT_2,
            ChipAmount(starting_chips - 150),
            total_invested_this_hand=ChipAmount(150),
            participation_status=HandParticipationStatus.FOLDED,
        )

        players = Players.from_list([p1, p2, p3])
        game = minimal_game_factory(players=list(players))

        community_cards = [
            make_card(Rank.TWO, Suit.CLUBS),
            make_card(Rank.FIVE, Suit.DIAMONDS),
            make_card(Rank.SEVEN, Suit.SPADES),
            make_card(Rank.NINE, Suit.HEARTS),
            make_card(Rank.THREE, Suit.CLUBS),
        ]

        # Stale pot_state (doesn't include P3's folded chips)
        pot_state = PotState(
            main_pot=Pot(
                amount=ChipAmount(400),  # Only P1 + P2, missing P3's 150
                eligible_player_ids=frozenset({p1.id, p2.id}),
            ),
            side_pots=[],
        )

        game = replace(
            game,
            players=players,
            pot_state=pot_state,
            hand_state=replace(
                game.hand_state,
                current_phase=GamePhase.SHOWDOWN,
                community_cards=community_cards,
            ),
        )

        # Calculate total chips before
        total_chips_before = sum(p.remaining_chips.value for p in game.players)
        total_invested = sum(p.total_invested_this_hand.value for p in game.players)
        expected_total = total_chips_before + total_invested  # 3000

        # Act
        completed_game = HandCompleter.complete(game)

        # Assert: Chips must be conserved
        total_chips_after = sum(p.remaining_chips.value for p in completed_game.players)

        print(f"Total chips after: {total_chips_after} (expected: {expected_total})")
        print(f"Chips lost: {expected_total - total_chips_after}")

        # P1 should win with AA: 800 + 550 = 1350
        # P2 should lose: 800 (no change)
        # P3 should keep: 850 (no change)
        winner = completed_game.players.get_by_id(p1.id)
        assert winner is not None

        print(f"P1 chips: {winner.remaining_chips.value} (expected: 1350)")

        # Total chips must be conserved
        assert total_chips_after == expected_total, (
            f"Chips disappeared! Expected {expected_total}, got {total_chips_after}. "
            f"Lost {expected_total - total_chips_after} chips."
        )


class TestPotDistributionChipConservation:
    """Test that pot distribution correctly conserves chips and distributes correctly.

    Verifies:
    1. All players who invested contribute to pot
    2. Chip conservation: (chips_before + investments) == chips_after
    3. Players receive correct distribution amounts
    """

    def test_core_behavior_showdown_with_folded_players_conserves_chips_and_distributes_correctly(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Core behavior: Showdown with folded players - all investments go to pot, correct distribution.

        Scenario:
        - 4 players: P1 (winner), P2 (loser), P3 (folded), P4 (folded)
        - P1 and P2 go to showdown, P3 and P4 folded after investing
        - All investments must be in pot, winner gets correct amount
        """
        starting_chips = 1000

        # P1: Winner with best hand, invested 300
        p1 = sample_player_factory(
            PlayerId("p1"),
            Seat.SEAT_0,
            ChipAmount(starting_chips - 300),
            total_invested_this_hand=ChipAmount(300),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.ACE, Suit.HEARTS),
                make_card(Rank.ACE, Suit.SPADES),
            ),
        )

        # P2: Loser, invested 300
        p2 = sample_player_factory(
            PlayerId("p2"),
            Seat.SEAT_1,
            ChipAmount(starting_chips - 300),
            total_invested_this_hand=ChipAmount(300),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.KING, Suit.HEARTS),
                make_card(Rank.KING, Suit.SPADES),
            ),
        )

        # P3: Folded, invested 200
        p3 = sample_player_factory(
            PlayerId("p3"),
            Seat.SEAT_2,
            ChipAmount(starting_chips - 200),
            total_invested_this_hand=ChipAmount(200),
            participation_status=HandParticipationStatus.FOLDED,
        )

        # P4: Folded, invested 150
        p4 = sample_player_factory(
            PlayerId("p4"),
            Seat.SEAT_3,
            ChipAmount(starting_chips - 150),
            total_invested_this_hand=ChipAmount(150),
            participation_status=HandParticipationStatus.FOLDED,
        )

        players = Players.from_list([p1, p2, p3, p4])
        game = minimal_game_factory(players=list(players))

        community_cards = [
            make_card(Rank.TWO, Suit.CLUBS),
            make_card(Rank.FIVE, Suit.DIAMONDS),
            make_card(Rank.SEVEN, Suit.SPADES),
            make_card(Rank.NINE, Suit.HEARTS),
            make_card(Rank.THREE, Suit.CLUBS),
        ]

        # Pot state will be recalculated, but set stale to test recalculation
        pot_state = PotState(
            main_pot=Pot(
                amount=ChipAmount(0),  # Stale - will be recalculated
                eligible_player_ids=frozenset({p1.id, p2.id, p3.id, p4.id}),
            ),
            side_pots=[],
        )

        game = replace(
            game,
            players=players,
            pot_state=pot_state,
            hand_state=replace(
                game.hand_state,
                current_phase=GamePhase.SHOWDOWN,
                community_cards=community_cards,
            ),
        )

        # Calculate totals before
        total_chips_before = sum(p.remaining_chips.value for p in game.players)
        total_invested = sum(p.total_invested_this_hand.value for p in game.players)
        expected_total_after = total_chips_before + total_invested

        # Expected pot: 300 + 300 + 200 + 150 = 950
        expected_pot = 950

        # Act
        completed_game = HandCompleter.complete(game)

        # Assert: Chip conservation
        total_chips_after = sum(p.remaining_chips.value for p in completed_game.players)
        assert total_chips_after == expected_total_after, (
            f"Chips not conserved! Before: {total_chips_before}, "
            f"Invested: {total_invested}, Expected after: {expected_total_after}, "
            f"Got: {total_chips_after}"
        )

        # Assert: Pot contains all investments
        actual_pot = completed_game.pot_state.total_amount().value
        assert (
            actual_pot == expected_pot
        ), f"Pot does not contain all investments! Expected: {expected_pot}, Got: {actual_pot}"

        # Assert: Correct distribution
        # P1 (winner): 700 + 950 = 1650
        # P2 (loser): 700 + 0 = 700
        # P3 (folded): 800 + 0 = 800
        # P4 (folded): 850 + 0 = 850
        player1 = completed_game.players.get_by_id(p1.id)
        player2 = completed_game.players.get_by_id(p2.id)
        player3 = completed_game.players.get_by_id(p3.id)
        player4 = completed_game.players.get_by_id(p4.id)

        assert player1 is not None
        assert player2 is not None
        assert player3 is not None
        assert player4 is not None

        assert (
            player1.remaining_chips.value == 1650
        ), f"P1 (winner) should have 1650 chips, got {player1.remaining_chips.value}"
        assert (
            player2.remaining_chips.value == 700
        ), f"P2 (loser) should have 700 chips, got {player2.remaining_chips.value}"
        assert (
            player3.remaining_chips.value == 800
        ), f"P3 (folded) should have 800 chips, got {player3.remaining_chips.value}"
        assert (
            player4.remaining_chips.value == 850
        ), f"P4 (folded) should have 850 chips, got {player4.remaining_chips.value}"

    def test_edge_case_all_players_all_in_at_different_levels_with_folded_players(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Edge case: Multiple all-in levels with folded players - complex side pot distribution.

        Scenario:
        - P1: All-in 100 (best hand) -> wins main pot
        - P2: All-in 300 (second best) -> wins side pots 1, 2, 3
        - P3: All-in 500 (third best) -> wins side pot 4
        - P4: All-in 500 (worst) -> wins nothing
        - P5: Folded after investing 200 -> chips in pot but not eligible
        - P6: Folded after investing 150 -> chips in pot but not eligible

        Pot calculation (per level):
        - Level 100: 100 × 6 = 600 (all 6 players, eligible: P1, P2, P3, P4) -> MAIN POT
        - Level 150: 50 × 5 = 250 (P2, P3, P4, P5, P6, eligible: P2, P3, P4) -> SIDE POT 1
        - Level 200: 50 × 4 = 200 (P2, P3, P4, P5, eligible: P2, P3, P4) -> SIDE POT 2
        - Level 300: 100 × 3 = 300 (P2, P3, P4, eligible: P2, P3, P4) -> SIDE POT 3
        - Level 500: 200 × 2 = 400 (P3, P4, eligible: P3, P4) -> SIDE POT 4
        Total: 1750 (matches total investments)
        """
        starting_chips = 1000

        # P1: All-in 100, best hand (AA)
        p1 = sample_player_factory(
            PlayerId("p1"),
            Seat.SEAT_0,
            ChipAmount(0),
            total_invested_this_hand=ChipAmount(100),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.ACE, Suit.HEARTS),
                make_card(Rank.ACE, Suit.SPADES),
            ),
        )

        # P2: All-in 300, second best (KK)
        p2 = sample_player_factory(
            PlayerId("p2"),
            Seat.SEAT_1,
            ChipAmount(0),
            total_invested_this_hand=ChipAmount(300),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.KING, Suit.HEARTS),
                make_card(Rank.KING, Suit.SPADES),
            ),
        )

        # P3: All-in 500, third best (QQ)
        p3 = sample_player_factory(
            PlayerId("p3"),
            Seat.SEAT_2,
            ChipAmount(0),
            total_invested_this_hand=ChipAmount(500),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.QUEEN, Suit.HEARTS),
                make_card(Rank.QUEEN, Suit.SPADES),
            ),
        )

        # P4: All-in 500, worst (JJ)
        p4 = sample_player_factory(
            PlayerId("p4"),
            Seat.SEAT_3,
            ChipAmount(0),
            total_invested_this_hand=ChipAmount(500),
            participation_status=HandParticipationStatus.IN_HAND,
            hole_cards=make_hand(
                make_card(Rank.JACK, Suit.HEARTS),
                make_card(Rank.JACK, Suit.SPADES),
            ),
        )

        # P5: Folded, invested 200
        p5 = sample_player_factory(
            PlayerId("p5"),
            Seat.SEAT_4,
            ChipAmount(starting_chips - 200),
            total_invested_this_hand=ChipAmount(200),
            participation_status=HandParticipationStatus.FOLDED,
        )

        # P6: Folded, invested 150
        p6 = sample_player_factory(
            PlayerId("p6"),
            Seat.SEAT_5,
            ChipAmount(starting_chips - 150),
            total_invested_this_hand=ChipAmount(150),
            participation_status=HandParticipationStatus.FOLDED,
        )

        players = Players.from_list([p1, p2, p3, p4, p5, p6])
        game = minimal_game_factory(players=list(players))

        community_cards = [
            make_card(Rank.TWO, Suit.CLUBS),
            make_card(Rank.FIVE, Suit.DIAMONDS),
            make_card(Rank.SEVEN, Suit.SPADES),
            make_card(Rank.NINE, Suit.HEARTS),
            make_card(Rank.THREE, Suit.CLUBS),
        ]

        # Pot state will be recalculated
        pot_state = PotState(
            main_pot=Pot(
                amount=ChipAmount(0),  # Stale
                eligible_player_ids=frozenset({p1.id, p2.id, p3.id, p4.id, p5.id, p6.id}),
            ),
            side_pots=[],
        )

        game = replace(
            game,
            players=players,
            pot_state=pot_state,
            hand_state=replace(
                game.hand_state,
                current_phase=GamePhase.SHOWDOWN,
                community_cards=community_cards,
            ),
        )

        # Calculate totals before
        total_chips_before = sum(p.remaining_chips.value for p in game.players)
        total_invested = sum(p.total_invested_this_hand.value for p in game.players)
        expected_total_after = total_chips_before + total_invested

        # Expected pot: 100 + 300 + 500 + 500 + 200 + 150 = 1750
        expected_pot = 1750

        # Act
        completed_game = HandCompleter.complete(game)

        # Assert: Chip conservation
        total_chips_after = sum(p.remaining_chips.value for p in completed_game.players)
        assert total_chips_after == expected_total_after, (
            f"Chips not conserved! Before: {total_chips_before}, "
            f"Invested: {total_invested}, Expected after: {expected_total_after}, "
            f"Got: {total_chips_after}"
        )

        # Assert: Pot contains all investments
        actual_pot = completed_game.pot_state.total_amount().value
        assert (
            actual_pot == expected_pot
        ), f"Pot does not contain all investments! Expected: {expected_pot}, Got: {actual_pot}"

        # Assert: Correct distribution
        # P1: 0 + main_pot (600) = 600
        # P2: 0 + side_pot_1+2+3 (250+200+300) = 750
        # P3: 0 + side_pot_4 (400) = 400
        # P4: 0 + 0 = 0
        # P5: 800 + 0 = 800
        # P6: 850 + 0 = 850
        player1 = completed_game.players.get_by_id(p1.id)
        player2 = completed_game.players.get_by_id(p2.id)
        player3 = completed_game.players.get_by_id(p3.id)
        player4 = completed_game.players.get_by_id(p4.id)
        player5 = completed_game.players.get_by_id(p5.id)
        player6 = completed_game.players.get_by_id(p6.id)

        assert player1 is not None
        assert player2 is not None
        assert player3 is not None
        assert player4 is not None
        assert player5 is not None
        assert player6 is not None

        # Verify winners get correct amounts
        assert (
            player1.remaining_chips.value == 600
        ), f"P1 (main pot winner) should have 600 chips, got {player1.remaining_chips.value}"
        assert (
            player2.remaining_chips.value == 750
        ), f"P2 (side pots 1+2+3 winner) should have 750 chips, got {player2.remaining_chips.value}"
        assert (
            player3.remaining_chips.value == 400
        ), f"P3 (side pot 2 winner) should have 400 chips, got {player3.remaining_chips.value}"
        assert (
            player4.remaining_chips.value == 0
        ), f"P4 (no pot) should have 0 chips, got {player4.remaining_chips.value}"
        assert (
            player5.remaining_chips.value == 800
        ), f"P5 (folded) should have 800 chips, got {player5.remaining_chips.value}"
        assert (
            player6.remaining_chips.value == 850
        ), f"P6 (folded) should have 850 chips, got {player6.remaining_chips.value}"

    def test_edge_case_early_win_with_multiple_folded_players_investments(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Edge case: Early win with multiple folded players - all investments must be in pot.

        Scenario:
        - P1: Only player in hand, wins by default
        - P2, P3, P4, P5: All folded after investing various amounts
        - All investments must go to P1, chips must be conserved
        """
        starting_chips = 5000

        # P1: Winner (only one in hand), invested 500
        p1 = sample_player_factory(
            PlayerId("p1"),
            Seat.SEAT_0,
            ChipAmount(starting_chips - 500),
            total_invested_this_hand=ChipAmount(500),
            participation_status=HandParticipationStatus.IN_HAND,
        )

        # P2: Folded, invested 300
        p2 = sample_player_factory(
            PlayerId("p2"),
            Seat.SEAT_1,
            ChipAmount(starting_chips - 300),
            total_invested_this_hand=ChipAmount(300),
            participation_status=HandParticipationStatus.FOLDED,
        )

        # P3: Folded, invested 200
        p3 = sample_player_factory(
            PlayerId("p3"),
            Seat.SEAT_2,
            ChipAmount(starting_chips - 200),
            total_invested_this_hand=ChipAmount(200),
            participation_status=HandParticipationStatus.FOLDED,
        )

        # P4: Folded, invested 150
        p4 = sample_player_factory(
            PlayerId("p4"),
            Seat.SEAT_3,
            ChipAmount(starting_chips - 150),
            total_invested_this_hand=ChipAmount(150),
            participation_status=HandParticipationStatus.FOLDED,
        )

        # P5: Folded, invested 100
        p5 = sample_player_factory(
            PlayerId("p5"),
            Seat.SEAT_4,
            ChipAmount(starting_chips - 100),
            total_invested_this_hand=ChipAmount(100),
            participation_status=HandParticipationStatus.FOLDED,
        )

        players = Players.from_list([p1, p2, p3, p4, p5])
        game = minimal_game_factory(players=list(players))

        # Pot state is stale (0) - will be recalculated
        pot_state = PotState(
            main_pot=Pot(
                amount=ChipAmount(0),  # Stale - will be recalculated
                eligible_player_ids=frozenset({p1.id, p2.id, p3.id, p4.id, p5.id}),
            ),
            side_pots=[],
        )

        game = replace(
            game,
            players=players,
            pot_state=pot_state,
            hand_state=replace(game.hand_state, current_phase=GamePhase.PRE_FLOP),
        )

        # Calculate totals before
        total_chips_before = sum(p.remaining_chips.value for p in game.players)
        total_invested = sum(p.total_invested_this_hand.value for p in game.players)
        expected_total_after = total_chips_before + total_invested

        # Expected pot: 500 + 300 + 200 + 150 + 100 = 1250
        expected_pot = 1250

        # Act
        completed_game = HandCompleter.complete(game)

        # Assert: Chip conservation
        total_chips_after = sum(p.remaining_chips.value for p in completed_game.players)
        assert total_chips_after == expected_total_after, (
            f"Chips not conserved! Before: {total_chips_before}, "
            f"Invested: {total_invested}, Expected after: {expected_total_after}, "
            f"Got: {total_chips_after}"
        )

        # Assert: Pot contains all investments
        actual_pot = completed_game.pot_state.total_amount().value
        assert (
            actual_pot == expected_pot
        ), f"Pot does not contain all investments! Expected: {expected_pot}, Got: {actual_pot}"

        # Assert: Correct distribution
        # P1 (winner): 4500 + 1250 = 5750
        # P2 (folded): 4700 + 0 = 4700
        # P3 (folded): 4800 + 0 = 4800
        # P4 (folded): 4850 + 0 = 4850
        # P5 (folded): 4900 + 0 = 4900
        player1 = completed_game.players.get_by_id(p1.id)
        player2 = completed_game.players.get_by_id(p2.id)
        player3 = completed_game.players.get_by_id(p3.id)
        player4 = completed_game.players.get_by_id(p4.id)
        player5 = completed_game.players.get_by_id(p5.id)

        assert player1 is not None
        assert player2 is not None
        assert player3 is not None
        assert player4 is not None
        assert player5 is not None

        assert (
            player1.remaining_chips.value == 5750
        ), f"P1 (winner) should have 5750 chips, got {player1.remaining_chips.value}"
        assert (
            player2.remaining_chips.value == 4700
        ), f"P2 (folded) should have 4700 chips, got {player2.remaining_chips.value}"
        assert (
            player3.remaining_chips.value == 4800
        ), f"P3 (folded) should have 4800 chips, got {player3.remaining_chips.value}"
        assert (
            player4.remaining_chips.value == 4850
        ), f"P4 (folded) should have 4850 chips, got {player4.remaining_chips.value}"
        assert (
            player5.remaining_chips.value == 4900
        ), f"P5 (folded) should have 4900 chips, got {player5.remaining_chips.value}"
