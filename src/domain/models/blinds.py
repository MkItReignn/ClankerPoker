from dataclasses import dataclass
from typing import Any

from src.domain.models.chips import ChipAmount


@dataclass(frozen=True, slots=True)
class BlindLevel:
    small_blind: ChipAmount
    big_blind: ChipAmount
    level: int

    def __post_init__(self) -> None:
        if self.level < 1:
            raise ValueError(f"Blind level must be at least 1: {self.level}")
        if self.big_blind.value < self.small_blind.value:
            raise ValueError(
                f"Big blind must be >= small blind: {self.big_blind.value} < {self.small_blind.value}"
            )
        if self.big_blind.value != self.small_blind.value * 2:
            raise ValueError(
                f"Big blind must be exactly 2x small blind: {self.big_blind.value} != {self.small_blind.value * 2}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "small_blind": self.small_blind.value,
            "big_blind": self.big_blind.value,
            "level": self.level,
        }
