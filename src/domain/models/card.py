from dataclasses import dataclass
from enum import Enum
from typing import Any, Self


class Suit(Enum):
    HEARTS = "hearts"
    DIAMONDS = "diamonds"
    CLUBS = "clubs"
    SPADES = "spades"

    @property
    def ranking(self) -> int:
        _ranking: dict[Suit, int] = {
            Suit.SPADES: 4,
            Suit.HEARTS: 3,
            Suit.DIAMONDS: 2,
            Suit.CLUBS: 1,
        }
        return _ranking[self]

    @property
    def symbol(self) -> str:
        _symbols: dict[Suit, str] = {
            Suit.HEARTS: "❤️",
            Suit.DIAMONDS: "♦️",
            Suit.CLUBS: "♣️",
            Suit.SPADES: "♠️",
        }
        return _symbols[self]


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
    def from_short_string(cls, s: str) -> Self:
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

    def to_long_string(self) -> str:
        return {
            Rank.ACE: "Ace",
            Rank.KING: "King",
            Rank.QUEEN: "Queen",
            Rank.JACK: "Jack",
            Rank.TEN: "Ten",
            Rank.NINE: "Nine",
            Rank.EIGHT: "Eight",
            Rank.SEVEN: "Seven",
            Rank.SIX: "Six",
            Rank.FIVE: "Five",
            Rank.FOUR: "Four",
            Rank.THREE: "Three",
            Rank.TWO: "Two",
        }[self]

    def to_plural_string(self) -> str:
        if self == Rank.SIX:
            return "Sixes"
        return f"{self.to_long_string()}s"


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
        return f"{self.rank.to_short_string()}{self.suit.symbol}"

    def to_dict(self) -> dict[str, Any]:
        """Convert card to dictionary for JSON serialization."""
        return {
            "suit": self.suit.value,
            "rank": self.rank.to_short_string(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Reconstruct card from dictionary."""
        return cls(
            suit=Suit(data["suit"]),
            rank=Rank.from_short_string(data["rank"]),
        )
