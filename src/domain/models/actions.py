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
    POST_SMALL_BLIND = "post_small_blind"
    POST_BIG_BLIND = "post_big_blind"

    def to_short_string(self) -> str:
        """Convert action type to shorthand notation (F, X, C, B, R, AI, PSB, PBB)."""
        return {
            ActionType.FOLD: "F",
            ActionType.CHECK: "X",
            ActionType.CALL: "C",
            ActionType.BET: "B",
            ActionType.RAISE: "R",
            ActionType.ALL_IN: "AI",
            ActionType.POST_SMALL_BLIND: "PSB",
            ActionType.POST_BIG_BLIND: "PBB",
        }[self]


@dataclass(frozen=True, slots=True)
class Action:
    action_type: ActionType
    amount: ChipAmount | None = None

    def __post_init__(self) -> None:
        actions_requiring_amount = (
            ActionType.BET,
            ActionType.RAISE,
            ActionType.ALL_IN,
            ActionType.POST_SMALL_BLIND,
            ActionType.POST_BIG_BLIND,
        )
        actions_without_amount = (ActionType.FOLD, ActionType.CHECK, ActionType.CALL)

        if self.action_type in actions_requiring_amount:
            if self.amount is None:
                raise ValueError(f"{self.action_type.value} requires an amount")
            if self.amount.value <= 0:
                raise ValueError(
                    f"Amount must be positive for {self.action_type.value}: {self.amount.value}"
                )
        elif self.action_type in actions_without_amount:
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
