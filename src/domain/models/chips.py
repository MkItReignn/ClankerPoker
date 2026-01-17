from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ChipAmount:
    value: int

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError(f"ChipAmount cannot be negative: {self.value}")

    def __add__(self, other: ChipAmount) -> ChipAmount:
        return ChipAmount(self.value + other.value)

    def __sub__(self, other: ChipAmount) -> ChipAmount:
        result = self.value - other.value
        if result < 0:
            raise ValueError(
                f"Subtraction would result in negative amount: {self.value} - {other.value}"
            )
        return ChipAmount(result)

    def __mul__(self, multiplier: int) -> ChipAmount:
        if multiplier < 0:
            raise ValueError(f"Multiplier cannot be negative: {multiplier}")
        return ChipAmount(self.value * multiplier)

    def __lt__(self, other: ChipAmount) -> bool:
        return self.value < other.value

    def __le__(self, other: ChipAmount) -> bool:
        return self.value <= other.value

    def __gt__(self, other: ChipAmount) -> bool:
        return self.value > other.value

    def __ge__(self, other: ChipAmount) -> bool:
        return self.value >= other.value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ChipAmount):
            return NotImplemented
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)

    def to_dict(self) -> dict[str, Any]:
        """Convert chip amount to dictionary for JSON serialization.

        Note: ChipAmount is typically serialized directly as int in event metadata.
        This method exists for consistency with other domain models.
        """
        return {"value": self.value}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChipAmount:
        """Reconstruct chip amount from dictionary."""
        return cls(value=data["value"])
