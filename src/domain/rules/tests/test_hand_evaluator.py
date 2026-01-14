"""Tests for HandEvaluator - edge cases documenting poker rules."""

from __future__ import annotations

import pytest

from src.domain.models.card import Card, Rank, Suit
from src.domain.models.hand import Hand
from src.domain.rules.hand_evaluator import HandEvaluation, HandEvaluator, HandRank


class TestInvalidInputs:
    """Tests for invalid input handling."""

    def test_raises_error_when_fewer_than_five_community_cards(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.KING),
        )
        community_cards = [
            card_factory(suit=Suit.DIAMONDS, rank=Rank.QUEEN),
            card_factory(suit=Suit.CLUBS, rank=Rank.JACK),
            card_factory(suit=Suit.SPADES, rank=Rank.TEN),
        ]

        with pytest.raises(ValueError, match="Must have exactly 5 community cards"):
            HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

    def test_raises_error_when_more_than_five_community_cards(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.KING),
        )
        community_cards = [
            card_factory(suit=Suit.DIAMONDS, rank=Rank.QUEEN),
            card_factory(suit=Suit.CLUBS, rank=Rank.JACK),
            card_factory(suit=Suit.SPADES, rank=Rank.TEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.NINE),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.EIGHT),
            card_factory(suit=Suit.CLUBS, rank=Rank.SEVEN),
        ]

        with pytest.raises(ValueError, match="Must have exactly 5 community cards"):
            HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

    def test_raises_error_when_zero_community_cards(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.KING),
        )
        community_cards: list[Card] = []

        with pytest.raises(ValueError, match="Must have exactly 5 community cards"):
            HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)


class TestRoyalFlush:
    """Royal Flush: A-K-Q-J-10 all of the same suit (highest possible hand)."""

    def test_royal_flush_is_highest_hand_rank(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card2=card_factory(suit=Suit.SPADES, rank=Rank.KING),
        )
        community_cards = [
            card_factory(suit=Suit.SPADES, rank=Rank.QUEEN),
            card_factory(suit=Suit.SPADES, rank=Rank.JACK),
            card_factory(suit=Suit.SPADES, rank=Rank.TEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.TWO),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.THREE),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.ROYAL_FLUSH
        assert evaluation.kickers == (Rank.ACE,)

    def test_royal_flush_beats_straight_flush(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        royal_flush = HandEvaluation(
            rank=HandRank.ROYAL_FLUSH,
            cards_used=(),
            kickers=(Rank.ACE,),
        )
        straight_flush = HandEvaluation(
            rank=HandRank.STRAIGHT_FLUSH,
            cards_used=(),
            kickers=(Rank.KING,),
        )

        assert royal_flush.compare(straight_flush) > 0


class TestStraightFlush:
    """Straight Flush: Five consecutive cards of the same suit."""

    def test_straight_flush_king_high(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.HEARTS, rank=Rank.KING),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.QUEEN),
        )
        community_cards = [
            card_factory(suit=Suit.HEARTS, rank=Rank.JACK),
            card_factory(suit=Suit.HEARTS, rank=Rank.TEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.NINE),
            card_factory(suit=Suit.SPADES, rank=Rank.TWO),
            card_factory(suit=Suit.CLUBS, rank=Rank.THREE),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.STRAIGHT_FLUSH
        assert evaluation.kickers == (Rank.KING,)

    def test_straight_flush_wheel_is_lowest_straight_flush(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.DIAMONDS, rank=Rank.ACE),
            card2=card_factory(suit=Suit.DIAMONDS, rank=Rank.TWO),
        )
        community_cards = [
            card_factory(suit=Suit.DIAMONDS, rank=Rank.THREE),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.FOUR),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.FIVE),
            card_factory(suit=Suit.SPADES, rank=Rank.KING),
            card_factory(suit=Suit.HEARTS, rank=Rank.QUEEN),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.STRAIGHT_FLUSH
        assert evaluation.kickers == (Rank.FIVE,)

    def test_higher_straight_flush_beats_lower(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        high_straight_flush = HandEvaluation(
            rank=HandRank.STRAIGHT_FLUSH,
            cards_used=(),
            kickers=(Rank.KING,),
        )
        low_straight_flush = HandEvaluation(
            rank=HandRank.STRAIGHT_FLUSH,
            cards_used=(),
            kickers=(Rank.SIX,),
        )

        assert high_straight_flush.compare(low_straight_flush) > 0


class TestFourOfAKind:
    """Four of a Kind: Four cards of the same rank."""

    def test_four_of_a_kind_with_higher_kicker_beats_lower(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        four_kings_ace = HandEvaluation(
            rank=HandRank.FOUR_OF_A_KIND,
            cards_used=(),
            kickers=(Rank.KING, Rank.ACE),
        )
        four_kings_queen = HandEvaluation(
            rank=HandRank.FOUR_OF_A_KIND,
            cards_used=(),
            kickers=(Rank.KING, Rank.QUEEN),
        )

        assert four_kings_ace.compare(four_kings_queen) > 0

    def test_higher_four_of_a_kind_beats_lower(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        four_aces = HandEvaluation(
            rank=HandRank.FOUR_OF_A_KIND,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING),
        )
        four_kings = HandEvaluation(
            rank=HandRank.FOUR_OF_A_KIND,
            cards_used=(),
            kickers=(Rank.KING, Rank.ACE),
        )

        assert four_aces.compare(four_kings) > 0

    def test_four_of_a_kind_from_seven_cards_selects_best(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.ACE),
        )
        community_cards = [
            card_factory(suit=Suit.DIAMONDS, rank=Rank.ACE),
            card_factory(suit=Suit.CLUBS, rank=Rank.ACE),
            card_factory(suit=Suit.SPADES, rank=Rank.KING),
            card_factory(suit=Suit.HEARTS, rank=Rank.QUEEN),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.JACK),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.FOUR_OF_A_KIND
        assert evaluation.kickers[0] == Rank.ACE
        assert evaluation.kickers[1] == Rank.KING


class TestFullHouse:
    """Full House: Three of a kind plus a pair."""

    def test_full_house_three_of_a_kind_rank_determines_winner(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        three_aces_pair_kings = HandEvaluation(
            rank=HandRank.FULL_HOUSE,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING),
        )
        three_kings_pair_aces = HandEvaluation(
            rank=HandRank.FULL_HOUSE,
            cards_used=(),
            kickers=(Rank.KING, Rank.ACE),
        )

        assert three_aces_pair_kings.compare(three_kings_pair_aces) > 0

    def test_full_house_pair_rank_breaks_tie_when_three_of_a_kind_same(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        three_aces_pair_kings = HandEvaluation(
            rank=HandRank.FULL_HOUSE,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING),
        )
        three_aces_pair_queens = HandEvaluation(
            rank=HandRank.FULL_HOUSE,
            cards_used=(),
            kickers=(Rank.ACE, Rank.QUEEN),
        )

        assert three_aces_pair_kings.compare(three_aces_pair_queens) > 0

    def test_full_house_beats_flush(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        full_house = HandEvaluation(
            rank=HandRank.FULL_HOUSE,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING),
        )
        flush = HandEvaluation(
            rank=HandRank.FLUSH,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK, Rank.TEN),
        )

        assert full_house.compare(flush) > 0


class TestFlush:
    """Flush: Five cards of the same suit, not in sequence."""

    def test_flush_compares_highest_card_first(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        ace_high_flush = HandEvaluation(
            rank=HandRank.FLUSH,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK, Rank.NINE),
        )
        king_high_flush = HandEvaluation(
            rank=HandRank.FLUSH,
            cards_used=(),
            kickers=(Rank.KING, Rank.QUEEN, Rank.JACK, Rank.TEN, Rank.NINE),
        )

        assert ace_high_flush.compare(king_high_flush) > 0

    def test_flush_compares_second_highest_when_first_equal(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        ace_king_flush = HandEvaluation(
            rank=HandRank.FLUSH,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK, Rank.NINE),
        )
        ace_queen_flush = HandEvaluation(
            rank=HandRank.FLUSH,
            cards_used=(),
            kickers=(Rank.ACE, Rank.QUEEN, Rank.JACK, Rank.TEN, Rank.NINE),
        )

        assert ace_king_flush.compare(ace_queen_flush) > 0

    def test_flush_selects_best_five_from_seven_cards(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.HEARTS, rank=Rank.ACE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.KING),
        )
        community_cards = [
            card_factory(suit=Suit.HEARTS, rank=Rank.QUEEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.JACK),
            card_factory(suit=Suit.HEARTS, rank=Rank.FIVE),
            card_factory(suit=Suit.HEARTS, rank=Rank.TWO),
            card_factory(suit=Suit.SPADES, rank=Rank.THREE),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.FLUSH
        assert evaluation.kickers[0] == Rank.ACE
        assert evaluation.kickers[1] == Rank.KING
        assert evaluation.kickers[2] == Rank.QUEEN
        assert evaluation.kickers[3] == Rank.JACK
        assert evaluation.kickers[4] == Rank.FIVE


class TestStraight:
    """Straight: Five consecutive cards of different suits."""

    def test_wheel_straight_ace_low_is_lowest_straight(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.TWO),
        )
        community_cards = [
            card_factory(suit=Suit.DIAMONDS, rank=Rank.THREE),
            card_factory(suit=Suit.CLUBS, rank=Rank.FOUR),
            card_factory(suit=Suit.SPADES, rank=Rank.FIVE),
            card_factory(suit=Suit.HEARTS, rank=Rank.KING),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.QUEEN),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.STRAIGHT
        assert evaluation.kickers == (Rank.FIVE,)

    def test_wheel_straight_does_not_rank_ace_high(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        wheel_straight = HandEvaluation(
            rank=HandRank.STRAIGHT,
            cards_used=(),
            kickers=(Rank.FIVE,),
        )
        six_high_straight = HandEvaluation(
            rank=HandRank.STRAIGHT,
            cards_used=(),
            kickers=(Rank.SIX,),
        )

        assert wheel_straight.compare(six_high_straight) < 0

    def test_ace_high_straight_ten_to_ace(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.KING),
        )
        community_cards = [
            card_factory(suit=Suit.DIAMONDS, rank=Rank.QUEEN),
            card_factory(suit=Suit.CLUBS, rank=Rank.JACK),
            card_factory(suit=Suit.SPADES, rank=Rank.TEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.TWO),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.THREE),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.STRAIGHT
        assert evaluation.kickers == (Rank.ACE,)

    def test_higher_straight_beats_lower(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        ace_high_straight = HandEvaluation(
            rank=HandRank.STRAIGHT,
            cards_used=(),
            kickers=(Rank.ACE,),
        )
        king_high_straight = HandEvaluation(
            rank=HandRank.STRAIGHT,
            cards_used=(),
            kickers=(Rank.KING,),
        )

        assert ace_high_straight.compare(king_high_straight) > 0

    def test_straight_selects_best_from_seven_cards(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.SIX),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.SEVEN),
        )
        community_cards = [
            card_factory(suit=Suit.DIAMONDS, rank=Rank.EIGHT),
            card_factory(suit=Suit.CLUBS, rank=Rank.NINE),
            card_factory(suit=Suit.SPADES, rank=Rank.TEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.TWO),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.THREE),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.STRAIGHT
        assert evaluation.kickers == (Rank.TEN,)


class TestThreeOfAKind:
    """Three of a Kind: Three cards of the same rank."""

    def test_higher_three_of_a_kind_beats_lower(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        three_aces = HandEvaluation(
            rank=HandRank.THREE_OF_A_KIND,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN),
        )
        three_kings = HandEvaluation(
            rank=HandRank.THREE_OF_A_KIND,
            cards_used=(),
            kickers=(Rank.KING, Rank.ACE, Rank.QUEEN),
        )

        assert three_aces.compare(three_kings) > 0

    def test_three_of_a_kind_compares_first_kicker_when_rank_same(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        three_aces_king_queen = HandEvaluation(
            rank=HandRank.THREE_OF_A_KIND,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN),
        )
        three_aces_queen_jack = HandEvaluation(
            rank=HandRank.THREE_OF_A_KIND,
            cards_used=(),
            kickers=(Rank.ACE, Rank.QUEEN, Rank.JACK),
        )

        assert three_aces_king_queen.compare(three_aces_queen_jack) > 0

    def test_three_of_a_kind_compares_second_kicker_when_first_equal(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        three_aces_king_queen = HandEvaluation(
            rank=HandRank.THREE_OF_A_KIND,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN),
        )
        three_aces_king_jack = HandEvaluation(
            rank=HandRank.THREE_OF_A_KIND,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.JACK),
        )

        assert three_aces_king_queen.compare(three_aces_king_jack) > 0


class TestTwoPair:
    """Two Pair: Two different pairs."""

    def test_higher_top_pair_beats_lower(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        aces_kings = HandEvaluation(
            rank=HandRank.TWO_PAIR,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN),
        )
        kings_queens = HandEvaluation(
            rank=HandRank.TWO_PAIR,
            cards_used=(),
            kickers=(Rank.KING, Rank.QUEEN, Rank.JACK),
        )

        assert aces_kings.compare(kings_queens) > 0

    def test_higher_bottom_pair_beats_lower_when_top_pair_same(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        aces_kings = HandEvaluation(
            rank=HandRank.TWO_PAIR,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN),
        )
        aces_queens = HandEvaluation(
            rank=HandRank.TWO_PAIR,
            cards_used=(),
            kickers=(Rank.ACE, Rank.QUEEN, Rank.JACK),
        )

        assert aces_kings.compare(aces_queens) > 0

    def test_higher_kicker_beats_lower_when_both_pairs_same(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        aces_kings_queen = HandEvaluation(
            rank=HandRank.TWO_PAIR,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN),
        )
        aces_kings_jack = HandEvaluation(
            rank=HandRank.TWO_PAIR,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.JACK),
        )

        assert aces_kings_queen.compare(aces_kings_jack) > 0


class TestPair:
    """Pair: Two cards of the same rank."""

    def test_higher_pair_beats_lower(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        pair_aces = HandEvaluation(
            rank=HandRank.PAIR,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK),
        )
        pair_kings = HandEvaluation(
            rank=HandRank.PAIR,
            cards_used=(),
            kickers=(Rank.KING, Rank.ACE, Rank.QUEEN, Rank.JACK),
        )

        assert pair_aces.compare(pair_kings) > 0

    def test_higher_first_kicker_beats_lower_when_pair_same(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        pair_aces_king = HandEvaluation(
            rank=HandRank.PAIR,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK),
        )
        pair_aces_queen = HandEvaluation(
            rank=HandRank.PAIR,
            cards_used=(),
            kickers=(Rank.ACE, Rank.QUEEN, Rank.JACK, Rank.TEN),
        )

        assert pair_aces_king.compare(pair_aces_queen) > 0

    def test_higher_second_kicker_beats_lower_when_first_equal(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        pair_aces_king_queen = HandEvaluation(
            rank=HandRank.PAIR,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK),
        )
        pair_aces_king_jack = HandEvaluation(
            rank=HandRank.PAIR,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.JACK, Rank.TEN),
        )

        assert pair_aces_king_queen.compare(pair_aces_king_jack) > 0


class TestHighCard:
    """High Card: No pair or better, highest card wins."""

    def test_highest_card_beats_lower(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        ace_high = HandEvaluation(
            rank=HandRank.HIGH_CARD,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK, Rank.NINE),
        )
        king_high = HandEvaluation(
            rank=HandRank.HIGH_CARD,
            cards_used=(),
            kickers=(Rank.KING, Rank.QUEEN, Rank.JACK, Rank.TEN, Rank.NINE),
        )

        assert ace_high.compare(king_high) > 0

    def test_compares_second_card_when_first_equal(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        ace_king = HandEvaluation(
            rank=HandRank.HIGH_CARD,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK, Rank.NINE),
        )
        ace_queen = HandEvaluation(
            rank=HandRank.HIGH_CARD,
            cards_used=(),
            kickers=(Rank.ACE, Rank.QUEEN, Rank.JACK, Rank.TEN, Rank.NINE),
        )

        assert ace_king.compare(ace_queen) > 0

    def test_compares_all_five_cards_in_order(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        ace_king_queen_jack_nine = HandEvaluation(
            rank=HandRank.HIGH_CARD,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK, Rank.NINE),
        )
        ace_king_queen_jack_eight = HandEvaluation(
            rank=HandRank.HIGH_CARD,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK, Rank.EIGHT),
        )

        assert ace_king_queen_jack_nine.compare(ace_king_queen_jack_eight) > 0


class TestHandRankHierarchy:
    """Tests that verify hand ranks follow correct hierarchy."""

    def test_royal_flush_beats_all_other_hands(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        royal_flush = HandEvaluation(
            rank=HandRank.ROYAL_FLUSH,
            cards_used=(),
            kickers=(Rank.ACE,),
        )
        four_of_a_kind = HandEvaluation(
            rank=HandRank.FOUR_OF_A_KIND,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING),
        )

        assert royal_flush.compare(four_of_a_kind) > 0

    def test_straight_flush_beats_four_of_a_kind(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        straight_flush = HandEvaluation(
            rank=HandRank.STRAIGHT_FLUSH,
            cards_used=(),
            kickers=(Rank.KING,),
        )
        four_of_a_kind = HandEvaluation(
            rank=HandRank.FOUR_OF_A_KIND,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING),
        )

        assert straight_flush.compare(four_of_a_kind) > 0

    def test_four_of_a_kind_beats_full_house(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        four_of_a_kind = HandEvaluation(
            rank=HandRank.FOUR_OF_A_KIND,
            cards_used=(),
            kickers=(Rank.TWO, Rank.THREE),
        )
        full_house = HandEvaluation(
            rank=HandRank.FULL_HOUSE,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING),
        )

        assert four_of_a_kind.compare(full_house) > 0

    def test_full_house_beats_flush(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        full_house = HandEvaluation(
            rank=HandRank.FULL_HOUSE,
            cards_used=(),
            kickers=(Rank.TWO, Rank.THREE),
        )
        flush = HandEvaluation(
            rank=HandRank.FLUSH,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK, Rank.TEN),
        )

        assert full_house.compare(flush) > 0

    def test_flush_beats_straight(self, card_factory: type[Card], hand_factory: type[Hand]) -> None:
        flush = HandEvaluation(
            rank=HandRank.FLUSH,
            cards_used=(),
            kickers=(Rank.TWO, Rank.THREE, Rank.FOUR, Rank.FIVE, Rank.SIX),
        )
        straight = HandEvaluation(
            rank=HandRank.STRAIGHT,
            cards_used=(),
            kickers=(Rank.ACE,),
        )

        assert flush.compare(straight) > 0

    def test_straight_beats_three_of_a_kind(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        straight = HandEvaluation(
            rank=HandRank.STRAIGHT,
            cards_used=(),
            kickers=(Rank.FIVE,),
        )
        three_of_a_kind = HandEvaluation(
            rank=HandRank.THREE_OF_A_KIND,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN),
        )

        assert straight.compare(three_of_a_kind) > 0

    def test_three_of_a_kind_beats_two_pair(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        three_of_a_kind = HandEvaluation(
            rank=HandRank.THREE_OF_A_KIND,
            cards_used=(),
            kickers=(Rank.TWO, Rank.THREE, Rank.FOUR),
        )
        two_pair = HandEvaluation(
            rank=HandRank.TWO_PAIR,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN),
        )

        assert three_of_a_kind.compare(two_pair) > 0

    def test_two_pair_beats_pair(self, card_factory: type[Card], hand_factory: type[Hand]) -> None:
        two_pair = HandEvaluation(
            rank=HandRank.TWO_PAIR,
            cards_used=(),
            kickers=(Rank.TWO, Rank.THREE, Rank.FOUR),
        )
        pair = HandEvaluation(
            rank=HandRank.PAIR,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK),
        )

        assert two_pair.compare(pair) > 0

    def test_pair_beats_high_card(self, card_factory: type[Card], hand_factory: type[Hand]) -> None:
        pair = HandEvaluation(
            rank=HandRank.PAIR,
            cards_used=(),
            kickers=(Rank.TWO, Rank.THREE, Rank.FOUR, Rank.FIVE),
        )
        high_card = HandEvaluation(
            rank=HandRank.HIGH_CARD,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK, Rank.TEN),
        )

        assert pair.compare(high_card) > 0

    def test_pair_of_aces_beats_high_card_with_same_community_cards(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        """Test scenario from determine_winners test: pair of aces vs high card.

        Community cards must not form a straight or flush, so pair beats high card.
        """
        pair_player_hole = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.ACE),
        )
        high_card_player_hole = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.KING),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.QUEEN),
        )
        community_cards = [
            card_factory(suit=Suit.CLUBS, rank=Rank.TWO),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.THREE),
            card_factory(suit=Suit.SPADES, rank=Rank.FOUR),
            card_factory(suit=Suit.HEARTS, rank=Rank.SIX),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.SEVEN),
        ]

        pair_eval = HandEvaluator.evaluate_hand_strength(pair_player_hole, community_cards)
        high_card_eval = HandEvaluator.evaluate_hand_strength(
            high_card_player_hole, community_cards
        )

        assert pair_eval.rank == HandRank.PAIR
        assert high_card_eval.rank == HandRank.HIGH_CARD
        assert pair_eval.compare(high_card_eval) > 0


class TestBestFiveCardSelection:
    """Tests that verify best 5-card hand is selected from 7 cards."""

    def test_selects_straight_over_pair_when_both_possible(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.KING),
        )
        community_cards = [
            card_factory(suit=Suit.DIAMONDS, rank=Rank.QUEEN),
            card_factory(suit=Suit.CLUBS, rank=Rank.JACK),
            card_factory(suit=Suit.SPADES, rank=Rank.TEN),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.ACE),
            card_factory(suit=Suit.HEARTS, rank=Rank.TWO),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.STRAIGHT

    def test_selects_flush_over_straight_when_both_possible(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.HEARTS, rank=Rank.ACE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.KING),
        )
        community_cards = [
            card_factory(suit=Suit.HEARTS, rank=Rank.QUEEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.JACK),
            card_factory(suit=Suit.HEARTS, rank=Rank.NINE),
            card_factory(suit=Suit.SPADES, rank=Rank.TEN),
            card_factory(suit=Suit.SPADES, rank=Rank.NINE),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.FLUSH

    def test_selects_higher_straight_when_multiple_straights_possible(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.SIX),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.SEVEN),
        )
        community_cards = [
            card_factory(suit=Suit.DIAMONDS, rank=Rank.EIGHT),
            card_factory(suit=Suit.CLUBS, rank=Rank.NINE),
            card_factory(suit=Suit.SPADES, rank=Rank.TEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.TWO),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.THREE),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.STRAIGHT
        assert evaluation.kickers == (Rank.TEN,)

    def test_selects_full_house_over_two_pair_when_both_possible(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.ACE),
        )
        community_cards = [
            card_factory(suit=Suit.DIAMONDS, rank=Rank.ACE),
            card_factory(suit=Suit.CLUBS, rank=Rank.KING),
            card_factory(suit=Suit.SPADES, rank=Rank.KING),
            card_factory(suit=Suit.HEARTS, rank=Rank.QUEEN),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.JACK),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.FULL_HOUSE


class TestTieScenarios:
    """Tests for scenarios where hands tie."""

    def test_identical_hands_tie(self, card_factory: type[Card], hand_factory: type[Hand]) -> None:
        hand1 = HandEvaluation(
            rank=HandRank.PAIR,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK),
        )
        hand2 = HandEvaluation(
            rank=HandRank.PAIR,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK),
        )

        assert hand1.compare(hand2) == 0

    def test_identical_straights_tie(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        straight1 = HandEvaluation(
            rank=HandRank.STRAIGHT,
            cards_used=(),
            kickers=(Rank.TEN,),
        )
        straight2 = HandEvaluation(
            rank=HandRank.STRAIGHT,
            cards_used=(),
            kickers=(Rank.TEN,),
        )

        assert straight1.compare(straight2) == 0


class TestStraightFlushEdgeCases:
    """Edge cases for straight flush detection and selection."""

    def test_selects_straight_flush_over_regular_flush_when_both_possible(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.HEARTS, rank=Rank.NINE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.TEN),
        )
        community_cards = [
            card_factory(suit=Suit.HEARTS, rank=Rank.JACK),
            card_factory(suit=Suit.HEARTS, rank=Rank.QUEEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.KING),
            card_factory(suit=Suit.HEARTS, rank=Rank.TWO),
            card_factory(suit=Suit.SPADES, rank=Rank.THREE),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.STRAIGHT_FLUSH

    def test_selects_straight_flush_over_regular_straight_when_both_possible(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.SIX),
            card2=card_factory(suit=Suit.SPADES, rank=Rank.SEVEN),
        )
        community_cards = [
            card_factory(suit=Suit.SPADES, rank=Rank.EIGHT),
            card_factory(suit=Suit.SPADES, rank=Rank.NINE),
            card_factory(suit=Suit.SPADES, rank=Rank.TEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.SIX),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.SEVEN),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.STRAIGHT_FLUSH

    def test_selects_royal_flush_over_straight_flush_when_both_possible(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card2=card_factory(suit=Suit.SPADES, rank=Rank.KING),
        )
        community_cards = [
            card_factory(suit=Suit.SPADES, rank=Rank.QUEEN),
            card_factory(suit=Suit.SPADES, rank=Rank.JACK),
            card_factory(suit=Suit.SPADES, rank=Rank.TEN),
            card_factory(suit=Suit.SPADES, rank=Rank.NINE),
            card_factory(suit=Suit.HEARTS, rank=Rank.TWO),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.ROYAL_FLUSH


class TestMultiplePossibleHands:
    """Tests for scenarios where multiple hand types are possible from 7 cards."""

    def test_selects_higher_straight_when_two_straights_possible(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.FIVE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.SIX),
        )
        community_cards = [
            card_factory(suit=Suit.DIAMONDS, rank=Rank.SEVEN),
            card_factory(suit=Suit.CLUBS, rank=Rank.EIGHT),
            card_factory(suit=Suit.SPADES, rank=Rank.NINE),
            card_factory(suit=Suit.HEARTS, rank=Rank.TEN),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.TWO),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.STRAIGHT
        assert evaluation.kickers == (Rank.TEN,)

    def test_selects_best_flush_when_six_cards_same_suit(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.HEARTS, rank=Rank.ACE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.KING),
        )
        community_cards = [
            card_factory(suit=Suit.HEARTS, rank=Rank.QUEEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.JACK),
            card_factory(suit=Suit.HEARTS, rank=Rank.NINE),
            card_factory(suit=Suit.HEARTS, rank=Rank.TWO),
            card_factory(suit=Suit.SPADES, rank=Rank.THREE),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.FLUSH
        assert evaluation.kickers[0] == Rank.ACE
        assert evaluation.kickers[1] == Rank.KING
        assert evaluation.kickers[2] == Rank.QUEEN
        assert evaluation.kickers[3] == Rank.JACK
        assert evaluation.kickers[4] == Rank.NINE

    def test_selects_best_two_pair_when_three_pairs_possible(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.ACE),
        )
        community_cards = [
            card_factory(suit=Suit.DIAMONDS, rank=Rank.KING),
            card_factory(suit=Suit.CLUBS, rank=Rank.KING),
            card_factory(suit=Suit.SPADES, rank=Rank.QUEEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.QUEEN),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.JACK),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.TWO_PAIR
        assert evaluation.kickers[0] == Rank.ACE
        assert evaluation.kickers[1] == Rank.KING
        assert evaluation.kickers[2] == Rank.QUEEN


class TestFullHouseEdgeCases:
    """Edge cases for full house detection."""

    def test_pair_and_three_of_a_kind_forms_full_house(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.ACE),
        )
        community_cards = [
            card_factory(suit=Suit.DIAMONDS, rank=Rank.ACE),
            card_factory(suit=Suit.CLUBS, rank=Rank.KING),
            card_factory(suit=Suit.SPADES, rank=Rank.KING),
            card_factory(suit=Suit.HEARTS, rank=Rank.QUEEN),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.JACK),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.FULL_HOUSE
        assert evaluation.kickers[0] == Rank.ACE
        assert evaluation.kickers[1] == Rank.KING

    def test_four_of_a_kind_with_pair_still_four_of_a_kind_not_full_house(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.ACE),
        )
        community_cards = [
            card_factory(suit=Suit.DIAMONDS, rank=Rank.ACE),
            card_factory(suit=Suit.CLUBS, rank=Rank.ACE),
            card_factory(suit=Suit.SPADES, rank=Rank.KING),
            card_factory(suit=Suit.HEARTS, rank=Rank.KING),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.QUEEN),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.FOUR_OF_A_KIND
        assert evaluation.kickers[0] == Rank.ACE
        assert evaluation.kickers[1] == Rank.KING


class TestKickerComparisons:
    """Comprehensive kicker comparison tests for all hand types."""

    def test_pair_compares_third_kicker_when_first_two_equal(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        pair_aces_king_queen = HandEvaluation(
            rank=HandRank.PAIR,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK),
        )
        pair_aces_king_jack = HandEvaluation(
            rank=HandRank.PAIR,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.JACK, Rank.TEN),
        )

        assert pair_aces_king_queen.compare(pair_aces_king_jack) > 0

    def test_pair_compares_fourth_kicker_when_first_three_equal(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        pair_aces_king_queen_jack = HandEvaluation(
            rank=HandRank.PAIR,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK),
        )
        pair_aces_king_queen_ten = HandEvaluation(
            rank=HandRank.PAIR,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN, Rank.TEN),
        )

        assert pair_aces_king_queen_jack.compare(pair_aces_king_queen_ten) > 0

    def test_flush_compares_third_card_when_first_two_equal(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        ace_king_queen_flush = HandEvaluation(
            rank=HandRank.FLUSH,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK, Rank.NINE),
        )
        ace_king_jack_flush = HandEvaluation(
            rank=HandRank.FLUSH,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.JACK, Rank.TEN, Rank.NINE),
        )

        assert ace_king_queen_flush.compare(ace_king_jack_flush) > 0

    def test_flush_compares_fourth_card_when_first_three_equal(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        ace_king_queen_jack_flush = HandEvaluation(
            rank=HandRank.FLUSH,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK, Rank.NINE),
        )
        ace_king_queen_ten_flush = HandEvaluation(
            rank=HandRank.FLUSH,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN, Rank.TEN, Rank.NINE),
        )

        assert ace_king_queen_jack_flush.compare(ace_king_queen_ten_flush) > 0

    def test_flush_compares_fifth_card_when_first_four_equal(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        ace_king_queen_jack_ten_flush = HandEvaluation(
            rank=HandRank.FLUSH,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK, Rank.TEN),
        )
        ace_king_queen_jack_nine_flush = HandEvaluation(
            rank=HandRank.FLUSH,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK, Rank.NINE),
        )

        assert ace_king_queen_jack_ten_flush.compare(ace_king_queen_jack_nine_flush) > 0

    def test_high_card_compares_third_card_when_first_two_equal(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        ace_king_queen_high = HandEvaluation(
            rank=HandRank.HIGH_CARD,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK, Rank.NINE),
        )
        ace_king_jack_high = HandEvaluation(
            rank=HandRank.HIGH_CARD,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.JACK, Rank.TEN, Rank.NINE),
        )

        assert ace_king_queen_high.compare(ace_king_jack_high) > 0

    def test_high_card_compares_fourth_card_when_first_three_equal(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        ace_king_queen_jack_high = HandEvaluation(
            rank=HandRank.HIGH_CARD,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK, Rank.NINE),
        )
        ace_king_queen_ten_high = HandEvaluation(
            rank=HandRank.HIGH_CARD,
            cards_used=(),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN, Rank.TEN, Rank.NINE),
        )

        assert ace_king_queen_jack_high.compare(ace_king_queen_ten_high) > 0


class TestWheelStraightEdgeCases:
    """Edge cases for wheel straight (A-2-3-4-5) detection."""

    def test_wheel_straight_with_ace_in_hole_cards(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.TWO),
        )
        community_cards = [
            card_factory(suit=Suit.DIAMONDS, rank=Rank.THREE),
            card_factory(suit=Suit.CLUBS, rank=Rank.FOUR),
            card_factory(suit=Suit.SPADES, rank=Rank.FIVE),
            card_factory(suit=Suit.HEARTS, rank=Rank.KING),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.QUEEN),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.STRAIGHT
        assert evaluation.kickers == (Rank.FIVE,)

    def test_wheel_straight_with_ace_in_community_cards(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.TWO),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.THREE),
        )
        community_cards = [
            card_factory(suit=Suit.DIAMONDS, rank=Rank.FOUR),
            card_factory(suit=Suit.CLUBS, rank=Rank.FIVE),
            card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card_factory(suit=Suit.HEARTS, rank=Rank.KING),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.QUEEN),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.STRAIGHT
        assert evaluation.kickers == (Rank.FIVE,)

    def test_wheel_straight_does_not_form_with_ace_high_straight_available(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.KING),
        )
        community_cards = [
            card_factory(suit=Suit.DIAMONDS, rank=Rank.QUEEN),
            card_factory(suit=Suit.CLUBS, rank=Rank.JACK),
            card_factory(suit=Suit.SPADES, rank=Rank.TEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.TWO),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.THREE),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.STRAIGHT
        assert evaluation.kickers == (Rank.ACE,)


class TestInvalidStraightScenarios:
    """Tests that verify invalid straight scenarios are not detected."""

    def test_wrap_around_straight_king_ace_two_three_four_not_valid(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.KING),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.ACE),
        )
        community_cards = [
            card_factory(suit=Suit.DIAMONDS, rank=Rank.TWO),
            card_factory(suit=Suit.CLUBS, rank=Rank.THREE),
            card_factory(suit=Suit.SPADES, rank=Rank.FOUR),
            card_factory(suit=Suit.HEARTS, rank=Rank.QUEEN),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.JACK),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank != HandRank.STRAIGHT
        assert evaluation.rank == HandRank.HIGH_CARD


class TestRoyalFlushEdgeCases:
    """Edge cases for royal flush detection."""

    def test_royal_flush_detected_in_all_suits(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        for suit in [Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS, Suit.SPADES]:
            hole_cards = hand_factory(
                card1=card_factory(suit=suit, rank=Rank.ACE),
                card2=card_factory(suit=suit, rank=Rank.KING),
            )
            community_cards = [
                card_factory(suit=suit, rank=Rank.QUEEN),
                card_factory(suit=suit, rank=Rank.JACK),
                card_factory(suit=suit, rank=Rank.TEN),
                card_factory(
                    suit=Suit.HEARTS if suit != Suit.HEARTS else Suit.DIAMONDS, rank=Rank.TWO
                ),
                card_factory(suit=Suit.CLUBS, rank=Rank.THREE),
            ]

            evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

            assert evaluation.rank == HandRank.ROYAL_FLUSH
            assert evaluation.kickers == (Rank.ACE,)


class TestComparisonEdgeCases:
    """Edge cases for hand comparison logic."""

    def test_compare_returns_negative_when_hand_is_weaker(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        weaker = HandEvaluation(
            rank=HandRank.PAIR,
            cards_used=(),
            kickers=(Rank.TWO, Rank.THREE, Rank.FOUR, Rank.FIVE),
        )
        stronger = HandEvaluation(
            rank=HandRank.THREE_OF_A_KIND,
            cards_used=(),
            kickers=(Rank.TWO, Rank.THREE, Rank.FOUR),
        )

        assert weaker.compare(stronger) < 0
        assert stronger.compare(weaker) > 0

    def test_compare_handles_all_hand_ranks_correctly(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        ranks = [
            HandRank.HIGH_CARD,
            HandRank.PAIR,
            HandRank.TWO_PAIR,
            HandRank.THREE_OF_A_KIND,
            HandRank.STRAIGHT,
            HandRank.FLUSH,
            HandRank.FULL_HOUSE,
            HandRank.FOUR_OF_A_KIND,
            HandRank.STRAIGHT_FLUSH,
            HandRank.ROYAL_FLUSH,
        ]

        for i in range(len(ranks) - 1):
            lower = HandEvaluation(
                rank=ranks[i],
                cards_used=(),
                kickers=(Rank.ACE,),
            )
            higher = HandEvaluation(
                rank=ranks[i + 1],
                cards_used=(),
                kickers=(Rank.TWO,),
            )

            assert lower.compare(higher) < 0
            assert higher.compare(lower) > 0


class TestComplexSevenCardScenarios:
    """Complex scenarios with all 7 cards that test best hand selection."""

    def test_selects_straight_flush_when_straight_and_flush_both_possible(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.HEARTS, rank=Rank.SEVEN),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.EIGHT),
        )
        community_cards = [
            card_factory(suit=Suit.HEARTS, rank=Rank.NINE),
            card_factory(suit=Suit.HEARTS, rank=Rank.TEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.JACK),
            card_factory(suit=Suit.SPADES, rank=Rank.SEVEN),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.EIGHT),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.STRAIGHT_FLUSH

    def test_selects_best_hand_when_multiple_combinations_possible(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.ACE),
        )
        community_cards = [
            card_factory(suit=Suit.DIAMONDS, rank=Rank.ACE),
            card_factory(suit=Suit.CLUBS, rank=Rank.KING),
            card_factory(suit=Suit.SPADES, rank=Rank.KING),
            card_factory(suit=Suit.HEARTS, rank=Rank.QUEEN),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.QUEEN),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.FULL_HOUSE
        assert evaluation.kickers[0] == Rank.ACE
        assert evaluation.kickers[1] == Rank.KING


class TestPlayingTheBoard:
    """Tests for scenarios where the best hand is on the board (chop situations)."""

    def test_board_straight_beats_hole_card_pair(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.TWO),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.TWO),
        )
        community_cards = [
            card_factory(suit=Suit.DIAMONDS, rank=Rank.TEN),
            card_factory(suit=Suit.CLUBS, rank=Rank.JACK),
            card_factory(suit=Suit.SPADES, rank=Rank.QUEEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.KING),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.ACE),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.STRAIGHT
        assert evaluation.kickers == (Rank.ACE,)

    def test_board_flush_is_best_hand(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.CLUBS, rank=Rank.TWO),
            card2=card_factory(suit=Suit.CLUBS, rank=Rank.THREE),
        )
        community_cards = [
            card_factory(suit=Suit.HEARTS, rank=Rank.ACE),
            card_factory(suit=Suit.HEARTS, rank=Rank.KING),
            card_factory(suit=Suit.HEARTS, rank=Rank.QUEEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.JACK),
            card_factory(suit=Suit.HEARTS, rank=Rank.NINE),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.FLUSH
        assert evaluation.kickers[0] == Rank.ACE

    def test_identical_hands_when_playing_board(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards_player1 = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.TWO),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.THREE),
        )
        hole_cards_player2 = hand_factory(
            card1=card_factory(suit=Suit.CLUBS, rank=Rank.FOUR),
            card2=card_factory(suit=Suit.DIAMONDS, rank=Rank.FIVE),
        )
        community_cards = [
            card_factory(suit=Suit.HEARTS, rank=Rank.ACE),
            card_factory(suit=Suit.HEARTS, rank=Rank.KING),
            card_factory(suit=Suit.HEARTS, rank=Rank.QUEEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.JACK),
            card_factory(suit=Suit.HEARTS, rank=Rank.TEN),
        ]

        eval1 = HandEvaluator.evaluate_hand_strength(hole_cards_player1, community_cards)
        eval2 = HandEvaluator.evaluate_hand_strength(hole_cards_player2, community_cards)

        assert eval1.rank == HandRank.ROYAL_FLUSH
        assert eval2.rank == HandRank.ROYAL_FLUSH
        assert eval1.compare(eval2) == 0


class TestCounterfeitScenarios:
    """Tests for scenarios where hole cards get counterfeited by the board."""

    def test_two_pair_counterfeited_by_higher_board_pairs(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.THREE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.FOUR),
        )
        community_cards = [
            card_factory(suit=Suit.DIAMONDS, rank=Rank.ACE),
            card_factory(suit=Suit.CLUBS, rank=Rank.ACE),
            card_factory(suit=Suit.SPADES, rank=Rank.KING),
            card_factory(suit=Suit.HEARTS, rank=Rank.KING),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.QUEEN),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.TWO_PAIR
        assert evaluation.kickers[0] == Rank.ACE
        assert evaluation.kickers[1] == Rank.KING
        assert evaluation.kickers[2] == Rank.QUEEN

    def test_pair_counterfeited_by_board_trips(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.TWO),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.TWO),
        )
        community_cards = [
            card_factory(suit=Suit.DIAMONDS, rank=Rank.ACE),
            card_factory(suit=Suit.CLUBS, rank=Rank.ACE),
            card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card_factory(suit=Suit.HEARTS, rank=Rank.KING),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.QUEEN),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.FULL_HOUSE
        assert evaluation.kickers[0] == Rank.ACE
        assert evaluation.kickers[1] == Rank.TWO


class TestSplitPotKickerScenarios:
    """Tests for scenarios where kicker determines winner in split pot situations."""

    def test_same_pair_different_second_kicker(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards_player1 = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.QUEEN),
        )
        hole_cards_player2 = hand_factory(
            card1=card_factory(suit=Suit.CLUBS, rank=Rank.ACE),
            card2=card_factory(suit=Suit.DIAMONDS, rank=Rank.JACK),
        )
        community_cards = [
            card_factory(suit=Suit.HEARTS, rank=Rank.KING),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.KING),
            card_factory(suit=Suit.SPADES, rank=Rank.SIX),
            card_factory(suit=Suit.HEARTS, rank=Rank.FIVE),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.THREE),
        ]

        eval1 = HandEvaluator.evaluate_hand_strength(hole_cards_player1, community_cards)
        eval2 = HandEvaluator.evaluate_hand_strength(hole_cards_player2, community_cards)

        assert eval1.rank == HandRank.PAIR
        assert eval2.rank == HandRank.PAIR
        assert eval1.kickers == (Rank.KING, Rank.ACE, Rank.QUEEN, Rank.SIX)
        assert eval2.kickers == (Rank.KING, Rank.ACE, Rank.JACK, Rank.SIX)
        assert eval1.compare(eval2) > 0

    def test_high_card_fifth_kicker_decides(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        hole_cards_player1 = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.EIGHT),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.THREE),
        )
        hole_cards_player2 = hand_factory(
            card1=card_factory(suit=Suit.CLUBS, rank=Rank.SEVEN),
            card2=card_factory(suit=Suit.DIAMONDS, rank=Rank.THREE),
        )
        community_cards = [
            card_factory(suit=Suit.HEARTS, rank=Rank.ACE),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.KING),
            card_factory(suit=Suit.SPADES, rank=Rank.QUEEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.JACK),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.TWO),
        ]

        eval1 = HandEvaluator.evaluate_hand_strength(hole_cards_player1, community_cards)
        eval2 = HandEvaluator.evaluate_hand_strength(hole_cards_player2, community_cards)

        assert eval1.rank == HandRank.HIGH_CARD
        assert eval2.rank == HandRank.HIGH_CARD
        assert eval1.kickers == (Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK, Rank.EIGHT)
        assert eval2.kickers == (Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK, Rank.SEVEN)
        assert eval1.compare(eval2) > 0


class TestFlushSuitIrrelevance:
    """Tests that verify suit is irrelevant for flush comparison - only ranks matter."""

    def test_flush_same_ranks_tie_when_playing_board(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        """Two players playing the same board flush tie - suit of hole cards irrelevant."""
        hole_cards_player1 = hand_factory(
            card1=card_factory(suit=Suit.CLUBS, rank=Rank.TWO),
            card2=card_factory(suit=Suit.DIAMONDS, rank=Rank.THREE),
        )
        hole_cards_player2 = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.TWO),
            card2=card_factory(suit=Suit.CLUBS, rank=Rank.THREE),
        )
        # Board has a hearts flush - neither player can improve it
        community_cards = [
            card_factory(suit=Suit.HEARTS, rank=Rank.KING),
            card_factory(suit=Suit.HEARTS, rank=Rank.QUEEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.JACK),
            card_factory(suit=Suit.HEARTS, rank=Rank.NINE),
            card_factory(suit=Suit.HEARTS, rank=Rank.SEVEN),
        ]

        eval1 = HandEvaluator.evaluate_hand_strength(hole_cards_player1, community_cards)
        eval2 = HandEvaluator.evaluate_hand_strength(hole_cards_player2, community_cards)

        assert eval1.rank == HandRank.FLUSH
        assert eval2.rank == HandRank.FLUSH
        assert eval1.kickers == eval2.kickers
        assert eval1.compare(eval2) == 0

    def test_flush_player_improves_board_flush_wins(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        """Player with suited Ace improves board flush, beats player playing board."""
        # Player 1 has Ace of hearts - can improve the flush
        hole_cards_player1 = hand_factory(
            card1=card_factory(suit=Suit.HEARTS, rank=Rank.ACE),
            card2=card_factory(suit=Suit.DIAMONDS, rank=Rank.THREE),
        )
        # Player 2 has no hearts - plays the board
        hole_cards_player2 = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.TWO),
            card2=card_factory(suit=Suit.CLUBS, rank=Rank.THREE),
        )
        # Board has a hearts flush K-Q-J-9-7
        community_cards = [
            card_factory(suit=Suit.HEARTS, rank=Rank.KING),
            card_factory(suit=Suit.HEARTS, rank=Rank.QUEEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.JACK),
            card_factory(suit=Suit.HEARTS, rank=Rank.NINE),
            card_factory(suit=Suit.HEARTS, rank=Rank.SEVEN),
        ]

        eval1 = HandEvaluator.evaluate_hand_strength(hole_cards_player1, community_cards)
        eval2 = HandEvaluator.evaluate_hand_strength(hole_cards_player2, community_cards)

        assert eval1.rank == HandRank.FLUSH
        assert eval2.rank == HandRank.FLUSH
        # Player 1 has A-K-Q-J-9, Player 2 has K-Q-J-9-7
        assert eval1.kickers[0] == Rank.ACE
        assert eval2.kickers[0] == Rank.KING
        assert eval1.compare(eval2) > 0

    def test_flush_ranks_determine_winner_not_hole_card_suits(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        """When both improve a flush, ranks determine winner regardless of suits."""
        # Player 1 has Ace of hearts - improves to A-K-Q-9-7
        hole_cards_player1 = hand_factory(
            card1=card_factory(suit=Suit.HEARTS, rank=Rank.ACE),
            card2=card_factory(suit=Suit.DIAMONDS, rank=Rank.THREE),
        )
        # Player 2 has Ten of hearts - improves to K-Q-T-9-7
        hole_cards_player2 = hand_factory(
            card1=card_factory(suit=Suit.HEARTS, rank=Rank.TEN),
            card2=card_factory(suit=Suit.CLUBS, rank=Rank.THREE),
        )
        # Board has hearts K-Q-9-7-4 (no straight flush possible)
        community_cards = [
            card_factory(suit=Suit.HEARTS, rank=Rank.KING),
            card_factory(suit=Suit.HEARTS, rank=Rank.QUEEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.NINE),
            card_factory(suit=Suit.HEARTS, rank=Rank.SEVEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.FOUR),
        ]

        eval1 = HandEvaluator.evaluate_hand_strength(hole_cards_player1, community_cards)
        eval2 = HandEvaluator.evaluate_hand_strength(hole_cards_player2, community_cards)

        assert eval1.rank == HandRank.FLUSH
        assert eval2.rank == HandRank.FLUSH
        assert eval1.kickers[0] == Rank.ACE
        assert eval2.kickers[0] == Rank.KING
        assert eval1.compare(eval2) > 0


class TestAllTwentyOneCombinations:
    """Tests that verify all 21 combinations of 7 cards (C(7,5)) are evaluated."""

    def test_all_combinations_evaluated_when_multiple_hand_types_possible(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        """Test that best hand is selected from all 21 possible 5-card combinations."""
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.HEARTS, rank=Rank.NINE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.EIGHT),
        )
        community_cards = [
            card_factory(suit=Suit.HEARTS, rank=Rank.SEVEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.FIVE),
            card_factory(suit=Suit.HEARTS, rank=Rank.THREE),
            card_factory(suit=Suit.SPADES, rank=Rank.NINE),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.NINE),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.FLUSH
        assert evaluation.kickers[0] == Rank.NINE
        assert evaluation.kickers[1] == Rank.EIGHT
        assert evaluation.kickers[2] == Rank.SEVEN
        assert evaluation.kickers[3] == Rank.FIVE
        assert evaluation.kickers[4] == Rank.THREE

    def test_all_combinations_evaluated_straight_vs_pair(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        """Verify all 21 combinations are checked when straight and pair both possible."""
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.SIX),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.SEVEN),
        )
        community_cards = [
            card_factory(suit=Suit.DIAMONDS, rank=Rank.EIGHT),
            card_factory(suit=Suit.CLUBS, rank=Rank.NINE),
            card_factory(suit=Suit.SPADES, rank=Rank.TEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.SIX),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.SIX),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.STRAIGHT
        assert evaluation.kickers == (Rank.TEN,)

    def test_all_combinations_evaluated_full_house_vs_two_pair(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        """Verify all 21 combinations checked when full house and two pair both possible."""
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.ACE),
        )
        community_cards = [
            card_factory(suit=Suit.DIAMONDS, rank=Rank.ACE),
            card_factory(suit=Suit.CLUBS, rank=Rank.KING),
            card_factory(suit=Suit.SPADES, rank=Rank.KING),
            card_factory(suit=Suit.HEARTS, rank=Rank.QUEEN),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.QUEEN),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.FULL_HOUSE
        assert evaluation.kickers[0] == Rank.ACE
        assert evaluation.kickers[1] == Rank.KING

    def test_all_combinations_evaluated_straight_flush_vs_four_of_a_kind(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        """Verify all 21 combinations checked when straight flush and four of a kind both possible."""
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.HEARTS, rank=Rank.NINE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.TEN),
        )
        community_cards = [
            card_factory(suit=Suit.HEARTS, rank=Rank.JACK),
            card_factory(suit=Suit.HEARTS, rank=Rank.QUEEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.KING),
            card_factory(suit=Suit.SPADES, rank=Rank.NINE),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.NINE),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.STRAIGHT_FLUSH
        assert evaluation.kickers == (Rank.KING,)

    def test_all_combinations_evaluated_when_six_cards_same_suit(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        """Verify all 21 combinations evaluated when 6 cards are same suit (15 flush combinations)."""
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.HEARTS, rank=Rank.NINE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.EIGHT),
        )
        community_cards = [
            card_factory(suit=Suit.HEARTS, rank=Rank.SEVEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.FIVE),
            card_factory(suit=Suit.HEARTS, rank=Rank.THREE),
            card_factory(suit=Suit.HEARTS, rank=Rank.TWO),
            card_factory(suit=Suit.SPADES, rank=Rank.FOUR),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.FLUSH
        assert evaluation.kickers[0] == Rank.NINE
        assert evaluation.kickers[1] == Rank.EIGHT
        assert evaluation.kickers[2] == Rank.SEVEN
        assert evaluation.kickers[3] == Rank.FIVE
        assert evaluation.kickers[4] == Rank.THREE

    def test_all_combinations_evaluated_complex_scenario(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        """Complex scenario where multiple hand types are possible from different 5-card combinations."""
        hole_cards = hand_factory(
            card1=card_factory(suit=Suit.HEARTS, rank=Rank.SEVEN),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.EIGHT),
        )
        community_cards = [
            card_factory(suit=Suit.HEARTS, rank=Rank.NINE),
            card_factory(suit=Suit.HEARTS, rank=Rank.TEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.JACK),
            card_factory(suit=Suit.SPADES, rank=Rank.SEVEN),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.SEVEN),
        ]

        evaluation = HandEvaluator.evaluate_hand_strength(hole_cards, community_cards)

        assert evaluation.rank == HandRank.STRAIGHT_FLUSH
        assert evaluation.kickers == (Rank.JACK,)


class TestComprehensiveTieScenarios:
    """Comprehensive tests for tie scenarios across all hand types."""

    def test_royal_flush_ties_when_both_play_board(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        """Two players playing the same board royal flush tie."""
        hole_cards_player1 = hand_factory(
            card1=card_factory(suit=Suit.CLUBS, rank=Rank.TWO),
            card2=card_factory(suit=Suit.DIAMONDS, rank=Rank.THREE),
        )
        hole_cards_player2 = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.TWO),
            card2=card_factory(suit=Suit.CLUBS, rank=Rank.THREE),
        )
        # Board has a royal flush in hearts
        community_cards = [
            card_factory(suit=Suit.HEARTS, rank=Rank.ACE),
            card_factory(suit=Suit.HEARTS, rank=Rank.KING),
            card_factory(suit=Suit.HEARTS, rank=Rank.QUEEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.JACK),
            card_factory(suit=Suit.HEARTS, rank=Rank.TEN),
        ]

        eval1 = HandEvaluator.evaluate_hand_strength(hole_cards_player1, community_cards)
        eval2 = HandEvaluator.evaluate_hand_strength(hole_cards_player2, community_cards)

        assert eval1.rank == HandRank.ROYAL_FLUSH
        assert eval2.rank == HandRank.ROYAL_FLUSH
        assert eval1.compare(eval2) == 0

    def test_straight_flush_ties_when_both_play_board(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        """Two players playing the same board straight flush tie."""
        hole_cards_player1 = hand_factory(
            card1=card_factory(suit=Suit.CLUBS, rank=Rank.TWO),
            card2=card_factory(suit=Suit.DIAMONDS, rank=Rank.THREE),
        )
        hole_cards_player2 = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.TWO),
            card2=card_factory(suit=Suit.CLUBS, rank=Rank.THREE),
        )
        # Board has a straight flush 9-K in hearts
        community_cards = [
            card_factory(suit=Suit.HEARTS, rank=Rank.KING),
            card_factory(suit=Suit.HEARTS, rank=Rank.QUEEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.JACK),
            card_factory(suit=Suit.HEARTS, rank=Rank.TEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.NINE),
        ]

        eval1 = HandEvaluator.evaluate_hand_strength(hole_cards_player1, community_cards)
        eval2 = HandEvaluator.evaluate_hand_strength(hole_cards_player2, community_cards)

        assert eval1.rank == HandRank.STRAIGHT_FLUSH
        assert eval2.rank == HandRank.STRAIGHT_FLUSH
        assert eval1.compare(eval2) == 0

    def test_four_of_a_kind_ties_same_rank_same_kicker(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        """Four of a kind with same rank and same kicker should tie."""
        hole_cards_player1 = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.KING),
        )
        hole_cards_player2 = hand_factory(
            card1=card_factory(suit=Suit.DIAMONDS, rank=Rank.ACE),
            card2=card_factory(suit=Suit.CLUBS, rank=Rank.KING),
        )
        community_cards = [
            card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card_factory(suit=Suit.HEARTS, rank=Rank.ACE),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.ACE),
            card_factory(suit=Suit.CLUBS, rank=Rank.QUEEN),
            card_factory(suit=Suit.SPADES, rank=Rank.QUEEN),
        ]

        eval1 = HandEvaluator.evaluate_hand_strength(hole_cards_player1, community_cards)
        eval2 = HandEvaluator.evaluate_hand_strength(hole_cards_player2, community_cards)

        assert eval1.rank == HandRank.FOUR_OF_A_KIND
        assert eval2.rank == HandRank.FOUR_OF_A_KIND
        assert eval1.kickers == eval2.kickers
        assert eval1.compare(eval2) == 0

    def test_full_house_ties_same_three_of_a_kind_same_pair(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        """Full house with same three of a kind and same pair should tie."""
        hole_cards_player1 = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.KING),
        )
        hole_cards_player2 = hand_factory(
            card1=card_factory(suit=Suit.DIAMONDS, rank=Rank.ACE),
            card2=card_factory(suit=Suit.CLUBS, rank=Rank.KING),
        )
        community_cards = [
            card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card_factory(suit=Suit.HEARTS, rank=Rank.ACE),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.KING),
            card_factory(suit=Suit.CLUBS, rank=Rank.KING),
            card_factory(suit=Suit.SPADES, rank=Rank.QUEEN),
        ]

        eval1 = HandEvaluator.evaluate_hand_strength(hole_cards_player1, community_cards)
        eval2 = HandEvaluator.evaluate_hand_strength(hole_cards_player2, community_cards)

        assert eval1.rank == HandRank.FULL_HOUSE
        assert eval2.rank == HandRank.FULL_HOUSE
        assert eval1.kickers == eval2.kickers
        assert eval1.compare(eval2) == 0

    def test_straight_ties_same_high_card(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        """Straights with same high card should tie regardless of suits."""
        hole_cards_player1 = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.TEN),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.TWO),
        )
        hole_cards_player2 = hand_factory(
            card1=card_factory(suit=Suit.DIAMONDS, rank=Rank.TEN),
            card2=card_factory(suit=Suit.CLUBS, rank=Rank.TWO),
        )
        community_cards = [
            card_factory(suit=Suit.SPADES, rank=Rank.JACK),
            card_factory(suit=Suit.HEARTS, rank=Rank.QUEEN),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.KING),
            card_factory(suit=Suit.CLUBS, rank=Rank.ACE),
            card_factory(suit=Suit.SPADES, rank=Rank.THREE),
        ]

        eval1 = HandEvaluator.evaluate_hand_strength(hole_cards_player1, community_cards)
        eval2 = HandEvaluator.evaluate_hand_strength(hole_cards_player2, community_cards)

        assert eval1.rank == HandRank.STRAIGHT
        assert eval2.rank == HandRank.STRAIGHT
        assert eval1.kickers == eval2.kickers
        assert eval1.compare(eval2) == 0

    def test_three_of_a_kind_ties_same_rank_same_kickers(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        """Three of a kind with same rank and same kickers should tie."""
        hole_cards_player1 = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.KING),
        )
        hole_cards_player2 = hand_factory(
            card1=card_factory(suit=Suit.DIAMONDS, rank=Rank.ACE),
            card2=card_factory(suit=Suit.CLUBS, rank=Rank.KING),
        )
        community_cards = [
            card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card_factory(suit=Suit.HEARTS, rank=Rank.ACE),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.QUEEN),
            card_factory(suit=Suit.CLUBS, rank=Rank.JACK),
            card_factory(suit=Suit.SPADES, rank=Rank.TWO),
        ]

        eval1 = HandEvaluator.evaluate_hand_strength(hole_cards_player1, community_cards)
        eval2 = HandEvaluator.evaluate_hand_strength(hole_cards_player2, community_cards)

        assert eval1.rank == HandRank.THREE_OF_A_KIND
        assert eval2.rank == HandRank.THREE_OF_A_KIND
        assert eval1.kickers == eval2.kickers
        assert eval1.compare(eval2) == 0

    def test_two_pair_ties_same_pairs_same_kicker(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        """Two pair with same pairs and same kicker should tie."""
        hole_cards_player1 = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.KING),
        )
        hole_cards_player2 = hand_factory(
            card1=card_factory(suit=Suit.DIAMONDS, rank=Rank.ACE),
            card2=card_factory(suit=Suit.CLUBS, rank=Rank.KING),
        )
        community_cards = [
            card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card_factory(suit=Suit.HEARTS, rank=Rank.KING),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.QUEEN),
            card_factory(suit=Suit.CLUBS, rank=Rank.QUEEN),
            card_factory(suit=Suit.SPADES, rank=Rank.JACK),
        ]

        eval1 = HandEvaluator.evaluate_hand_strength(hole_cards_player1, community_cards)
        eval2 = HandEvaluator.evaluate_hand_strength(hole_cards_player2, community_cards)

        assert eval1.rank == HandRank.TWO_PAIR
        assert eval2.rank == HandRank.TWO_PAIR
        assert eval1.kickers == eval2.kickers
        assert eval1.compare(eval2) == 0

    def test_pair_ties_same_pair_same_kickers(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        """Pair with same pair rank and same kickers should tie."""
        hole_cards_player1 = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.KING),
        )
        hole_cards_player2 = hand_factory(
            card1=card_factory(suit=Suit.DIAMONDS, rank=Rank.ACE),
            card2=card_factory(suit=Suit.CLUBS, rank=Rank.KING),
        )
        community_cards = [
            card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card_factory(suit=Suit.HEARTS, rank=Rank.QUEEN),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.JACK),
            card_factory(suit=Suit.CLUBS, rank=Rank.TWO),
            card_factory(suit=Suit.SPADES, rank=Rank.THREE),
        ]

        eval1 = HandEvaluator.evaluate_hand_strength(hole_cards_player1, community_cards)
        eval2 = HandEvaluator.evaluate_hand_strength(hole_cards_player2, community_cards)

        assert eval1.rank == HandRank.PAIR
        assert eval2.rank == HandRank.PAIR
        assert eval1.kickers == eval2.kickers
        assert eval1.compare(eval2) == 0

    def test_high_card_ties_same_ranks(
        self, card_factory: type[Card], hand_factory: type[Hand]
    ) -> None:
        """High card hands with same ranks should tie regardless of suits."""
        hole_cards_player1 = hand_factory(
            card1=card_factory(suit=Suit.SPADES, rank=Rank.ACE),
            card2=card_factory(suit=Suit.HEARTS, rank=Rank.KING),
        )
        hole_cards_player2 = hand_factory(
            card1=card_factory(suit=Suit.DIAMONDS, rank=Rank.ACE),
            card2=card_factory(suit=Suit.CLUBS, rank=Rank.KING),
        )
        community_cards = [
            card_factory(suit=Suit.SPADES, rank=Rank.QUEEN),
            card_factory(suit=Suit.HEARTS, rank=Rank.JACK),
            card_factory(suit=Suit.DIAMONDS, rank=Rank.NINE),
            card_factory(suit=Suit.CLUBS, rank=Rank.SEVEN),
            card_factory(suit=Suit.SPADES, rank=Rank.FIVE),
        ]

        eval1 = HandEvaluator.evaluate_hand_strength(hole_cards_player1, community_cards)
        eval2 = HandEvaluator.evaluate_hand_strength(hole_cards_player2, community_cards)

        assert eval1.rank == HandRank.HIGH_CARD
        assert eval2.rank == HandRank.HIGH_CARD
        assert eval1.kickers == eval2.kickers
        assert eval1.compare(eval2) == 0
