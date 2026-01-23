from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.domain.models.card import Card


@dataclass(frozen=True, slots=True)
class Hand:
    card1: Card
    card2: Card

    def __post_init__(self) -> None:
        if self.card1 == self.card2:
            raise ValueError("Hand cannot contain duplicate cards")

    @property
    def cards(self) -> tuple[Card, Card]:
        return (self.card1, self.card2)

    def __str__(self) -> str:
        return f"{self.card1} {self.card2}"

    def to_dict(self) -> list[dict[str, Any]]:
        return [self.card1.to_dict(), self.card2.to_dict()]
