from dataclasses import dataclass
from random import Random
from typing import Self

from src.domain.models.card import Card, Rank, Suit

STANDARD_DECK: list[Card] = [
    Card(suit=suit, rank=rank) for suit in Suit for rank in Rank
]


@dataclass(slots=True)
class Deck:
    cards: list[Card]
    _deal_index: int = 0

    def __post_init__(self) -> None:
        if len(self.cards) != 52:
            raise ValueError(
                f"Deck must have exactly 52 cards, got {len(self.cards)}"
            )
        if len(set(self.cards)) != 52:
            raise ValueError("Deck contains duplicate cards")

    @classmethod
    def create_shuffled(cls, seed: int | None = None) -> Self:
        rng = Random(seed) if seed is not None else Random()
        shuffled = STANDARD_DECK.copy()
        rng.shuffle(shuffled)

        return cls(cards=shuffled, _deal_index=0)

    def deal_card(self) -> Card:
        if self._deal_index >= len(self.cards):
            raise ValueError("Cannot deal card: deck is empty")

        card = self.cards[self._deal_index]
        self._deal_index += 1
        return card

    def deal_cards(self, count: int) -> list[Card]:
        if self._deal_index + count > len(self.cards):
            raise ValueError(
                f"Cannot deal {count} cards: only {len(self.cards) - self._deal_index} remaining"
            )

        cards = self.cards[self._deal_index : self._deal_index + count]
        self._deal_index += count
        return cards

    def burn_card(self) -> None:
        if self._deal_index >= len(self.cards):
            raise ValueError("Cannot burn card: deck is empty")

        self._deal_index += 1

    def cards_remaining(self) -> int:
        return len(self.cards) - self._deal_index

    def is_empty(self) -> bool:
        return self._deal_index >= len(self.cards)
