from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.domain.models.chips import ChipAmount


class ActionType(Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all_in"


@dataclass(frozen=True, slots=True)
class Action:
    action_type: ActionType
    amount: ChipAmount | None = None

    def __post_init__(self) -> None:
        if self.action_type in (ActionType.BET, ActionType.RAISE, ActionType.ALL_IN):
            if self.amount is None:
                raise ValueError(f"{self.action_type.value} requires an amount")
            if self.amount.value <= 0:
                raise ValueError(
                    f"Amount must be positive for {self.action_type.value}: {self.amount.value}"
                )
        elif self.action_type in (ActionType.FOLD, ActionType.CHECK, ActionType.CALL):
            if self.amount is not None and self.amount.value > 0:
                raise ValueError(f"{self.action_type.value} cannot have an amount")
