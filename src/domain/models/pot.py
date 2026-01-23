from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.domain.models.chips import ChipAmount

PlayerId = str


@dataclass(frozen=True, slots=True)
class Pot:
    amount: ChipAmount
    eligible_player_ids: frozenset[PlayerId]

    def __post_init__(self) -> None:
        if self.amount.value < 0:
            raise ValueError(f"Pot amount cannot be negative: {self.amount.value}")
        if not self.eligible_player_ids:
            raise ValueError("Pot must have at least one eligible player")

    def is_eligible(self, player_id: PlayerId) -> bool:
        return player_id in self.eligible_player_ids

    def to_dict(self) -> dict[str, Any]:
        return {
            "amount": self.amount.value,
            "eligible_player_ids": list(self.eligible_player_ids),
        }


@dataclass(slots=True)
class PotState:
    main_pot: Pot
    side_pots: list[Pot]

    def __post_init__(self) -> None:
        if self.main_pot.amount.value < 0:
            raise ValueError(f"Main pot cannot be negative: {self.main_pot.amount.value}")
        for side_pot in self.side_pots:
            if side_pot.amount.value < 0:
                raise ValueError(f"Side pot cannot be negative: {side_pot.amount.value}")
            if not side_pot.eligible_player_ids:
                raise ValueError("Side pot must have at least one eligible player")

    def total_amount(self) -> ChipAmount:
        total = self.main_pot.amount
        for side_pot in self.side_pots:
            total = total + side_pot.amount
        return total

    def all_pots(self) -> list[Pot]:
        return [self.main_pot, *self.side_pots]

    def get_pots_for_player(self, player_id: PlayerId) -> list[Pot]:
        return [pot for pot in self.all_pots() if pot.is_eligible(player_id)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "main_pot": self.main_pot.to_dict(),
            "side_pots": [pot.to_dict() for pot in self.side_pots],
            "total": self.total_amount().value,
        }
