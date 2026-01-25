"""Poker-specific random action selection for mock providers."""

import random
from collections.abc import Sequence
from typing import ClassVar, Self

from src.domain.models.actions import Action, ActionType
from src.domain.models.available_action import (
    AvailableActions,
    AvailableAllInAction,
    AvailableBetAction,
    AvailableCallAction,
    AvailableCheckAction,
    AvailableFoldAction,
    AvailableRaiseAction,
)
from src.domain.models.chips import ChipAmount


class BotRandomActionSelector:
    """Selects random poker actions with configurable weights.

    Used by mock providers for testing and simulation.
    Weights can be configured to simulate different playing styles.
    """

    # Default weights for action selection
    DEFAULT_WEIGHTS: ClassVar[dict[ActionType, float]] = {
        ActionType.FOLD: 0.15,
        ActionType.CHECK: 0.30,
        ActionType.CALL: 0.25,
        ActionType.BET: 0.10,
        ActionType.RAISE: 0.10,
        ActionType.ALL_IN: 0.10,
    }

    def __init__(
        self,
        weights: dict[ActionType, float] | None = None,
        seed: int | None = None,
    ) -> None:
        """Initialize the action selector.

        Args:
            weights: Optional custom weights for action types.
            seed: Optional random seed for reproducibility.
        """
        self._weights = weights or self.DEFAULT_WEIGHTS
        self._rng = random.Random(seed)

    def select_action(
        self,
        available_actions: Sequence[AvailableActions],
    ) -> Action:
        """Select a random action from available actions.

        Uses weighted random selection based on configured weights.
        Falls back to uniform random if no weighted actions available.

        Args:
            available_actions: The available actions to choose from.

        Returns:
            A randomly selected Action.

        Raises:
            ValueError: If no available actions.
        """
        if not available_actions:
            raise ValueError("No available actions to select from")

        # Build weighted selection based on action types
        weighted_actions: list[tuple[AvailableActions, float]] = []
        total_weight = 0.0

        for action in available_actions:
            weight = self._weights.get(action.action_type, 0.1)
            weighted_actions.append((action, weight))
            total_weight += weight

        # Select using weighted random
        if total_weight <= 0:
            # Fallback to uniform
            selected = self._rng.choice(list(available_actions))
        else:
            r = self._rng.random() * total_weight
            cumulative = 0.0
            selected = available_actions[0]  # Default
            for action, weight in weighted_actions:
                cumulative += weight
                if r <= cumulative:
                    selected = action
                    break

        return self._convert_to_action(selected)

    def _convert_to_action(self, available: AvailableActions) -> Action:
        """Convert an AvailableAction to an Action.

        For actions with ranges (bet/raise), selects a random amount
        within the valid range.
        """
        match available:
            case AvailableFoldAction():
                return Action(action_type=ActionType.FOLD)
            case AvailableCheckAction():
                return Action(action_type=ActionType.CHECK)
            case AvailableCallAction():
                return Action(action_type=ActionType.CALL)
            case AvailableAllInAction():
                return Action(
                    action_type=ActionType.ALL_IN,
                    amount=available.all_in_amount,
                )
            case AvailableBetAction():
                # Random amount within range, with bias toward smaller bets
                amount = self._select_amount_in_range(
                    available.min_bet_amount.value,
                    available.max_bet_amount.value,
                )
                return Action(
                    action_type=ActionType.BET,
                    amount=ChipAmount(amount),
                )
            case AvailableRaiseAction():
                # Random amount within range, with bias toward smaller raises
                amount = self._select_amount_in_range(
                    available.min_raise_amount.value,
                    available.max_raise_amount.value,
                )
                return Action(
                    action_type=ActionType.RAISE,
                    amount=ChipAmount(amount),
                )
            case _:
                raise ValueError(f"Unknown available action type: {available}")

    def _select_amount_in_range(self, min_amount: int, max_amount: int) -> int:
        """Select a random amount within range.

        Biased toward the lower end of the range to simulate
        more realistic betting patterns.
        """
        if min_amount >= max_amount:
            return min_amount

        # Use triangular distribution biased toward min
        amount = self._rng.triangular(
            low=float(min_amount),
            high=float(max_amount),
            mode=float(min_amount),  # Mode at min for lower-end bias
        )
        return int(amount)

    @classmethod
    def aggressive(cls, seed: int | None = None) -> Self:
        """Create an aggressive action selector.

        Prefers betting, raising, and going all-in.
        """
        weights = {
            ActionType.FOLD: 0.05,
            ActionType.CHECK: 0.10,
            ActionType.CALL: 0.15,
            ActionType.BET: 0.25,
            ActionType.RAISE: 0.25,
            ActionType.ALL_IN: 0.20,
        }
        return cls(weights=weights, seed=seed)

    @classmethod
    def passive(cls, seed: int | None = None) -> Self:
        """Create a passive action selector.

        Prefers checking, calling, and folding.
        """
        weights = {
            ActionType.FOLD: 0.25,
            ActionType.CHECK: 0.35,
            ActionType.CALL: 0.25,
            ActionType.BET: 0.05,
            ActionType.RAISE: 0.05,
            ActionType.ALL_IN: 0.05,
        }
        return cls(weights=weights, seed=seed)

    @classmethod
    def tight(cls, seed: int | None = None) -> Self:
        """Create a tight action selector.

        Folds frequently, but plays strong when not folding.
        """
        weights = {
            ActionType.FOLD: 0.40,
            ActionType.CHECK: 0.20,
            ActionType.CALL: 0.15,
            ActionType.BET: 0.10,
            ActionType.RAISE: 0.10,
            ActionType.ALL_IN: 0.05,
        }
        return cls(weights=weights, seed=seed)

    @classmethod
    def loose(cls, seed: int | None = None) -> Self:
        """Create a loose action selector.

        Rarely folds, stays in most hands.
        """
        weights = {
            ActionType.FOLD: 0.05,
            ActionType.CHECK: 0.30,
            ActionType.CALL: 0.35,
            ActionType.BET: 0.10,
            ActionType.RAISE: 0.10,
            ActionType.ALL_IN: 0.10,
        }
        return cls(weights=weights, seed=seed)
