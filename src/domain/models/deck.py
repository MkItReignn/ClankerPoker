from __future__ import annotations

from dataclasses import dataclass
from random import Random

from src.domain.models.card import Card, Rank, Suit

STANDARD_DECK: list[Card] = [Card(suit=suit, rank=rank) for suit in Suit for rank in Rank]


@dataclass(slots=True)
class Deck:
    """A pre-shuffled deck of 52 cards. Cards are dealt in sequence."""

    cards: list[Card]
    _deal_index: int = 0

    def __post_init__(self) -> None:
        if len(self.cards) != 52:
            raise ValueError(f"Deck must have exactly 52 cards, got {len(self.cards)}")
        if len(set(self.cards)) != 52:
            raise ValueError("Deck contains duplicate cards")

    @classmethod
    def create_shuffled(cls, seed: int | None = None) -> Deck:
        """Create a new shuffled deck. If seed is provided, deck is deterministic."""
        rng = Random(seed) if seed is not None else Random()
        shuffled = STANDARD_DECK.copy()
        rng.shuffle(shuffled)

        return cls(cards=shuffled, _deal_index=0)

    def deal_card(self) -> Card:
        """Deal the next card from the deck."""
        if self._deal_index >= len(self.cards):
            raise ValueError("Cannot deal card: deck is empty")

        card = self.cards[self._deal_index]
        self._deal_index += 1
        return card

    def deal_cards(self, count: int) -> list[Card]:
        """Deal multiple cards."""
        if self._deal_index + count > len(self.cards):
            raise ValueError(
                f"Cannot deal {count} cards: only {len(self.cards) - self._deal_index} remaining"
            )

        cards = self.cards[self._deal_index : self._deal_index + count]
        self._deal_index += count
        return cards

    def burn_card(self) -> None:
        """Burn the top card of the deck (remove it from play)."""
        if self._deal_index >= len(self.cards):
            raise ValueError("Cannot burn card: deck is empty")

        self._deal_index += 1

    def cards_remaining(self) -> int:
        """Return number of cards remaining in deck."""
        return len(self.cards) - self._deal_index

    def is_empty(self) -> bool:
        """Check if deck is empty."""
        return self._deal_index >= len(self.cards)
