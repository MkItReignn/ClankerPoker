from dataclasses import dataclass
from typing import Any

from src.domain.models.actions import ActionType
from src.domain.models.chips import ChipAmount


@dataclass(frozen=True, slots=True)
class AvailableFoldAction:
    action_type: ActionType = ActionType.FOLD

    def to_dict(self) -> dict[str, Any]:
        return {"action_type": self.action_type.value}


@dataclass(frozen=True, slots=True)
class AvailableCheckAction:
    action_type: ActionType = ActionType.CHECK

    def to_dict(self) -> dict[str, Any]:
        return {"action_type": self.action_type.value}


@dataclass(frozen=True, slots=True)
class AvailableCallAction:
    call_amount: ChipAmount
    action_type: ActionType = ActionType.CALL

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type.value,
            "call_amount": self.call_amount.value,
        }


@dataclass(frozen=True, slots=True)
class AvailableBetAction:
    min_bet_amount: ChipAmount
    max_bet_amount: ChipAmount
    action_type: ActionType = ActionType.BET

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type.value,
            "min_bet_amount": self.min_bet_amount.value,
            "max_bet_amount": self.max_bet_amount.value,
        }


@dataclass(frozen=True, slots=True)
class AvailableRaiseAction:
    min_raise_amount: ChipAmount
    max_raise_amount: ChipAmount
    action_type: ActionType = ActionType.RAISE

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type.value,
            "min_raise_amount": self.min_raise_amount.value,
            "max_raise_amount": self.max_raise_amount.value,
        }


@dataclass(frozen=True, slots=True)
class AvailableAllInAction:
    all_in_amount: ChipAmount
    action_type: ActionType = ActionType.ALL_IN

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type.value,
            "all_in_amount": self.all_in_amount.value,
        }


AvailableActions = (
    AvailableFoldAction
    | AvailableCheckAction
    | AvailableCallAction
    | AvailableBetAction
    | AvailableRaiseAction
    | AvailableAllInAction
)
