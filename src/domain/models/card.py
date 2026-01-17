from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Suit(Enum):
    HEARTS = "hearts"
    DIAMONDS = "diamonds"
    CLUBS = "clubs"
    SPADES = "spades"

    @property
    def ranking(self) -> int:
        """Suit ranking for tiebreakers: Spades > Hearts > Diamonds > Clubs."""
        _ranking: dict[Suit, int] = {
            Suit.SPADES: 4,
            Suit.HEARTS: 3,
            Suit.DIAMONDS: 2,
            Suit.CLUBS: 1,
        }
        return _ranking[self]


class Rank(Enum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14

    def to_short_string(self) -> str:
        """Convert rank to short string representation (A, K, Q, J, or number)."""
        return {
            Rank.ACE: "A",
            Rank.KING: "K",
            Rank.QUEEN: "Q",
            Rank.JACK: "J",
            Rank.TEN: "10",
            Rank.NINE: "9",
            Rank.EIGHT: "8",
            Rank.SEVEN: "7",
            Rank.SIX: "6",
            Rank.FIVE: "5",
            Rank.FOUR: "4",
            Rank.THREE: "3",
            Rank.TWO: "2",
        }[self]

    @classmethod
    def from_short_string(cls, s: str) -> Rank:
        """Parse rank from short string representation."""
        mapping = {
            "A": Rank.ACE,
            "K": Rank.KING,
            "Q": Rank.QUEEN,
            "J": Rank.JACK,
            "10": Rank.TEN,
            "9": Rank.NINE,
            "8": Rank.EIGHT,
            "7": Rank.SEVEN,
            "6": Rank.SIX,
            "5": Rank.FIVE,
            "4": Rank.FOUR,
            "3": Rank.THREE,
            "2": Rank.TWO,
        }
        if s not in mapping:
            raise ValueError(f"Invalid rank string: {s}")
        return mapping[s]


@dataclass(frozen=True, slots=True)
class Card:
    suit: Suit
    rank: Rank

    def __post_init__(self) -> None:
        if not isinstance(self.suit, Suit):
            raise ValueError(f"Invalid suit: {self.suit}")
        if not isinstance(self.rank, Rank):
            raise ValueError(f"Invalid rank: {self.rank}")

    def __str__(self) -> str:
        rank_str = {
            Rank.ACE: "A",
            Rank.KING: "K",
            Rank.QUEEN: "Q",
            Rank.JACK: "J",
        }.get(self.rank, str(self.rank.value))
        suit_symbol = {
            Suit.HEARTS: "❤️",
            Suit.DIAMONDS: "♦️",
            Suit.CLUBS: "♣️",
            Suit.SPADES: "♠️",
        }[self.suit]
        return f"{rank_str}{suit_symbol}"

    def to_dict(self) -> dict[str, Any]:
        """Convert card to dictionary for JSON serialization."""
        return {
            "suit": self.suit.value,
            "rank": self.rank.to_short_string(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Card:
        """Reconstruct card from dictionary."""
        return cls(
            suit=Suit(data["suit"]),
            rank=Rank.from_short_string(data["rank"]),
        )
