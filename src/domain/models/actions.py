from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.domain.models.chips import ChipAmount


class ActionType(Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all_in"

    def to_short_string(self) -> str:
        """Convert action type to shorthand notation (F, X, C, B, R, AI)."""
        return {
            ActionType.FOLD: "F",
            ActionType.CHECK: "X",
            ActionType.CALL: "C",
            ActionType.BET: "B",
            ActionType.RAISE: "R",
            ActionType.ALL_IN: "AI",
        }[self]


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

    def to_dict(self) -> dict[str, Any]:
        """Convert action to dictionary for JSON serialization."""
        return {
            "action_type": self.action_type.value,
            "amount": self.amount.value if self.amount else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Action:
        """Reconstruct action from dictionary."""
        return cls(
            action_type=ActionType(data["action_type"]),
            amount=ChipAmount(data["amount"]) if data["amount"] is not None else None,
        )
