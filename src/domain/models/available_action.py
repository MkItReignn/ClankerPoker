from __future__ import annotations

from dataclasses import dataclass

from src.domain.models.actions import ActionType
from src.domain.models.chips import ChipAmount


@dataclass(frozen=True, slots=True)
class AvailableFoldAction:
    action_type: ActionType = ActionType.FOLD


@dataclass(frozen=True, slots=True)
class AvailableCheckAction:
    action_type: ActionType = ActionType.CHECK


@dataclass(frozen=True, slots=True)
class AvailableCallAction:
    call_amount: ChipAmount
    action_type: ActionType = ActionType.CALL


@dataclass(frozen=True, slots=True)
class AvailableBetAction:
    min_bet_amount: ChipAmount
    max_bet_amount: ChipAmount
    action_type: ActionType = ActionType.BET


@dataclass(frozen=True, slots=True)
class AvailableRaiseAction:
    min_raise_amount: ChipAmount
    max_raise_amount: ChipAmount
    action_type: ActionType = ActionType.RAISE


@dataclass(frozen=True, slots=True)
class AvailableAllInAction:
    all_in_amount: ChipAmount
    action_type: ActionType = ActionType.ALL_IN


AvailableActions = (
    AvailableFoldAction
    | AvailableCheckAction
    | AvailableCallAction
    | AvailableBetAction
    | AvailableRaiseAction
    | AvailableAllInAction
)
