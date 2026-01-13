from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Suit(Enum):
    HEARTS = "hearts"
    DIAMONDS = "diamonds"
    CLUBS = "clubs"
    SPADES = "spades"


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
