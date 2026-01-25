from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from itertools import combinations
from typing import Any, override

from src.domain.models.card import Card, Rank
from src.domain.models.hand import Hand

WHEEL_STRAIGHT_RANKS = (
    Rank.TWO.value,
    Rank.THREE.value,
    Rank.FOUR.value,
    Rank.FIVE.value,
    Rank.ACE.value,
)

ROYAL_FLUSH_RANK_VALUES = [
    Rank.ACE.value,
    Rank.KING.value,
    Rank.QUEEN.value,
    Rank.JACK.value,
    Rank.TEN.value,
]


@dataclass(frozen=True, slots=True)
class CardRankFrequency:
    """Represents how many times a card rank appears in a hand."""

    frequency: int
    card_rank: Rank

    def __lt__(self, other: CardRankFrequency) -> bool:
        """Sort by frequency (descending), then by card rank value (descending)."""
        if self.frequency != other.frequency:
            return self.frequency < other.frequency
        return self.card_rank.value < other.card_rank.value


class HandRank(IntEnum):
    """Poker hand ranks ordered from weakest to strongest."""

    HIGH_CARD = 1
    PAIR = 2
    TWO_PAIR = 3
    THREE_OF_A_KIND = 4
    STRAIGHT = 5
    FLUSH = 6
    FULL_HOUSE = 7
    FOUR_OF_A_KIND = 8
    STRAIGHT_FLUSH = 9
    ROYAL_FLUSH = 10

    def __str__(self) -> str:
        """Get the human-readable label for this hand rank."""
        _names: dict[HandRank, str] = {
            HandRank.ROYAL_FLUSH: "Royal Flush",
            HandRank.STRAIGHT_FLUSH: "Straight Flush",
            HandRank.FOUR_OF_A_KIND: "Four of a Kind",
            HandRank.FULL_HOUSE: "Full House",
            HandRank.FLUSH: "Flush",
            HandRank.STRAIGHT: "Straight",
            HandRank.THREE_OF_A_KIND: "Three of a Kind",
            HandRank.TWO_PAIR: "Two Pair",
            HandRank.PAIR: "Pair",
            HandRank.HIGH_CARD: "High Card",
        }
        return _names[self]


@dataclass(frozen=True, slots=True)
class HandEvaluation:
    """Complete evaluation of a poker hand."""

    rank: HandRank
    cards_used: tuple[Card, ...]
    kickers: tuple[Rank, ...]

    @override
    def __str__(self) -> str:
        """Human-readable hand evaluation string."""
        cards_str = " ".join(str(card) for card in self.cards_used)
        kickers_str = " ".join(k.to_short_string() for k in self.kickers)
        return f"{self.rank} | ({cards_str}) | kickers: {kickers_str}"

    def compare(self, other: HandEvaluation) -> int:
        """
        Compare this hand to another hand.

        Returns:
            -1 if this hand is weaker than other
            0 if hands are equal (tie)
            1 if this hand is stronger than other
        """
        if self.rank < other.rank:
            return -1
        if self.rank > other.rank:
            return 1

        for kicker1, kicker2 in zip(self.kickers, other.kickers, strict=False):
            if kicker1.value < kicker2.value:
                return -1
            if kicker1.value > kicker2.value:
                return 1

        return 0

    def to_dict(self) -> dict[str, Any]:
        """Convert HandEvaluation to dictionary for serialization."""
        return {
            "rank": self.rank.value,
            "cards_used": [card.to_dict() for card in self.cards_used],
            "kickers": [kicker.value for kicker in self.kickers],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HandEvaluation:
        """Reconstruct HandEvaluation from dictionary."""
        return cls(
            rank=HandRank(data["rank"]),
            cards_used=tuple(Card.from_dict(c) for c in data["cards_used"]),
            kickers=tuple(Rank(k) for k in data["kickers"]),
        )


class HandEvaluator:
    """Evaluates poker hands and finds best 5-card combination."""

    @staticmethod
    def evaluate_hand_strength(
        hole_cards: Hand, community_cards: list[Card]
    ) -> HandEvaluation:
        """
        Evaluate the best 5-card hand from hole cards and community cards.

        Args:
            hole_cards: Player's 2 private cards
            community_cards: The 5 shared community cards

        Returns:
            HandEvaluation with the strongest possible 5-card hand

        Raises:
            ValueError: If invalid number of community cards
        """
        if len(community_cards) != 5:
            raise ValueError(
                f"Must have exactly 5 community cards for evaluation, got {len(community_cards)}"
            )

        all_7_cards = [hole_cards.card1, hole_cards.card2] + community_cards

        best_evaluation: HandEvaluation | None = None

        for five_cards in combinations(all_7_cards, 5):
            evaluation = HandEvaluator._evaluate_five_cards(list(five_cards))

            if (
                best_evaluation is None
                or evaluation.compare(best_evaluation) > 0
            ):
                best_evaluation = evaluation

        if best_evaluation is None:
            raise ValueError("Could not evaluate hand")

        return best_evaluation

    @staticmethod
    def _evaluate_five_cards(cards: list[Card]) -> HandEvaluation:
        """Evaluate a specific 5-card hand."""
        if len(cards) != 5:
            raise ValueError(f"Must have exactly 5 cards, got {len(cards)}")

        sorted_cards = sorted(cards, key=lambda c: c.rank.value, reverse=True)
        card_ranks = [card.rank for card in sorted_cards]
        rank_values = [card_rank.value for card_rank in card_ranks]
        suits = [card.suit for card in sorted_cards]

        is_flush = len(set(suits)) == 1
        is_straight = HandEvaluator._is_straight(rank_values)

        rank_counts = HandEvaluator._count_ranks(rank_values)
        sorted_rank_frequencies = sorted(
            [
                CardRankFrequency(frequency=count, card_rank=Rank(rank_value))
                for rank_value, count in rank_counts.items()
            ],
            reverse=True,
        )

        if is_straight and is_flush:
            straight_high_rank = HandEvaluator._get_straight_high_card_rank(
                rank_values
            )
            if straight_high_rank == Rank.ACE and sorted(
                set(rank_values)
            ) == sorted(ROYAL_FLUSH_RANK_VALUES):
                return HandEvaluation(
                    rank=HandRank.ROYAL_FLUSH,
                    cards_used=tuple(sorted_cards),
                    kickers=(Rank.ACE,),
                )
            return HandEvaluation(
                rank=HandRank.STRAIGHT_FLUSH,
                cards_used=tuple(sorted_cards),
                kickers=(straight_high_rank,),
            )

        if sorted_rank_frequencies[0].frequency == 4:
            four_of_a_kind_rank = sorted_rank_frequencies[0].card_rank
            if len(sorted_rank_frequencies) < 2:
                raise ValueError(
                    "Four of a kind requires at least two unique ranks"
                )
            kicker_rank = sorted_rank_frequencies[1].card_rank
            return HandEvaluation(
                rank=HandRank.FOUR_OF_A_KIND,
                cards_used=tuple(sorted_cards),
                kickers=(four_of_a_kind_rank, kicker_rank),
            )

        if (
            len(sorted_rank_frequencies) >= 2
            and sorted_rank_frequencies[0].frequency == 3
            and sorted_rank_frequencies[1].frequency == 2
        ):
            three_of_a_kind_rank = sorted_rank_frequencies[0].card_rank
            pair_rank = sorted_rank_frequencies[1].card_rank
            return HandEvaluation(
                rank=HandRank.FULL_HOUSE,
                cards_used=tuple(sorted_cards),
                kickers=(three_of_a_kind_rank, pair_rank),
            )

        if is_flush:
            return HandEvaluation(
                rank=HandRank.FLUSH,
                cards_used=tuple(sorted_cards),
                kickers=tuple(card_ranks),
            )

        if is_straight:
            straight_high_rank = HandEvaluator._get_straight_high_card_rank(
                rank_values
            )
            return HandEvaluation(
                rank=HandRank.STRAIGHT,
                cards_used=tuple(sorted_cards),
                kickers=(straight_high_rank,),
            )

        if sorted_rank_frequencies[0].frequency == 3:
            three_of_a_kind_rank = sorted_rank_frequencies[0].card_rank
            kicker_ranks = [three_of_a_kind_rank]
            kicker_ranks.extend(
                [
                    rank_frequency.card_rank
                    for rank_frequency in sorted_rank_frequencies[1:]
                ]
            )
            return HandEvaluation(
                rank=HandRank.THREE_OF_A_KIND,
                cards_used=tuple(sorted_cards),
                kickers=tuple(kicker_ranks),
            )

        if (
            len(sorted_rank_frequencies) >= 2
            and sorted_rank_frequencies[0].frequency == 2
            and sorted_rank_frequencies[1].frequency == 2
        ):
            first_pair_rank = sorted_rank_frequencies[0].card_rank
            second_pair_rank = sorted_rank_frequencies[1].card_rank
            pair_ranks_sorted = sorted(
                [first_pair_rank, second_pair_rank],
                key=lambda r: r.value,
                reverse=True,
            )
            kicker_ranks = pair_ranks_sorted + [
                rank_frequency.card_rank
                for rank_frequency in sorted_rank_frequencies[2:]
            ]
            return HandEvaluation(
                rank=HandRank.TWO_PAIR,
                cards_used=tuple(sorted_cards),
                kickers=tuple(kicker_ranks),
            )

        if sorted_rank_frequencies[0].frequency == 2:
            pair_rank = sorted_rank_frequencies[0].card_rank
            kicker_ranks = [pair_rank]
            kicker_ranks.extend(
                [
                    rank_frequency.card_rank
                    for rank_frequency in sorted_rank_frequencies[1:]
                ]
            )
            return HandEvaluation(
                rank=HandRank.PAIR,
                cards_used=tuple(sorted_cards),
                kickers=tuple(kicker_ranks),
            )

        return HandEvaluation(
            rank=HandRank.HIGH_CARD,
            cards_used=tuple(sorted_cards),
            kickers=tuple(card_ranks),
        )

    @staticmethod
    def _is_straight(rank_values: list[int]) -> bool:
        """Check if rank values form a straight (accounting for wheel straight)."""
        sorted_rank_values = sorted(set(rank_values))

        if len(sorted_rank_values) != 5:
            return False

        if sorted_rank_values == list(
            range(sorted_rank_values[0], sorted_rank_values[0] + 5)
        ):
            return True

        sorted_wheel_rank_values = sorted(WHEEL_STRAIGHT_RANKS)
        if sorted_rank_values == sorted_wheel_rank_values:
            return True

        return False

    @staticmethod
    def _get_straight_high_card_rank(rank_values: list[int]) -> Rank:
        """
        Get the high card rank for a straight.

        For wheel straight (A-2-3-4-5), returns Rank.FIVE (lowest straight).
        For all other straights, returns the highest card rank.
        """
        sorted_rank_values = sorted(set(rank_values))
        sorted_wheel = sorted(WHEEL_STRAIGHT_RANKS)

        if sorted_rank_values == sorted_wheel:
            return Rank.FIVE

        max_rank_value = max(sorted_rank_values)
        return Rank(max_rank_value)

    @staticmethod
    def _count_ranks(rank_values: list[int]) -> dict[int, int]:
        """Count occurrences of each rank value."""
        counts: dict[int, int] = {}
        for rank_value in rank_values:
            counts[rank_value] = counts.get(rank_value, 0) + 1
        return counts
