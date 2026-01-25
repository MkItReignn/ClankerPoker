"""Action parsing strategy for poker responses."""

import re
from typing import Protocol

from src.application.protocols.response import ParseError, ParseErrorType
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


class ActionParser(Protocol):
    """Protocol for parsing actions from response text."""

    def parse(
        self,
        response_text: str,
        available_actions: list[AvailableActions],
    ) -> Action | ParseError:
        """Parse action from text, validate, and create domain object.

        Args:
            response_text: The full LLM response text.
            available_actions: List of available actions to validate against.

        Returns:
            Action if parsing succeeded, or ParseError if it failed.
        """
        ...


class PokerActionParser:
    """Parses poker actions from LLM responses.

    Encapsulates extraction, validation, and creation as internal methods.
    """

    # Pattern to match ACTION: <type> [amount]
    ACTION_PATTERN = re.compile(
        r"ACTION:\s*(fold|check|call|bet|raise|allin|all-in|all_in)\s*(\d+)?",
        re.IGNORECASE,
    )

    def _normalize_action_type(self, action_str: str) -> str:
        """Normalize action type string."""
        normalized = action_str.lower().replace("-", "_")
        # Handle all-in variants
        if normalized in ("allin", "all_in"):
            return "all_in"
        return normalized

    def _extract(self, response_text: str) -> tuple[str, int | None] | None:
        """Internal: Extract action type and amount from text.

        Args:
            response_text: The full LLM response text.

        Returns:
            Tuple of (action_type, amount) if found, or None if not found.
            amount is None for actions that don't require amounts.
        """
        match = self.ACTION_PATTERN.search(response_text)
        if not match:
            return None

        action_type_str = match.group(1)
        amount_str = match.group(2)
        amount = int(amount_str) if amount_str else None

        # Normalize action type
        normalized_type = self._normalize_action_type(action_type_str)

        return (normalized_type, amount)

    def _validate_bet_amount(
        self,
        amount: int,
        action: AvailableBetAction,
        action_type: str,
    ) -> AvailableBetAction | ParseError:
        """Internal: Validate bet amount is within allowed range.

        Args:
            amount: The requested bet amount.
            action: The available bet action to validate against.
            action_type: The action type string for error context.

        Returns:
            AvailableBetAction if valid, or ParseError if validation failed.
        """
        if amount < action.min_bet_amount.value:
            return ParseError.create(
                ParseErrorType.AMOUNT_BELOW_MIN,
                f"Bet amount {amount} is below minimum {action.min_bet_amount.value}",
                context={
                    "requested_amount": amount,
                    "min_bet_amount": action.min_bet_amount.value,
                    "max_bet_amount": action.max_bet_amount.value,
                    "action_type": action_type,
                },
            )
        if amount > action.max_bet_amount.value:
            return ParseError.create(
                ParseErrorType.AMOUNT_ABOVE_MAX,
                f"Bet amount {amount} exceeds maximum {action.max_bet_amount.value}",
                context={
                    "requested_amount": amount,
                    "min_bet_amount": action.min_bet_amount.value,
                    "max_bet_amount": action.max_bet_amount.value,
                    "action_type": action_type,
                },
            )
        return action

    def _validate_raise_amount(
        self,
        amount: int,
        action: AvailableRaiseAction,
        action_type: str,
    ) -> AvailableRaiseAction | ParseError:
        """Internal: Validate raise amount is within allowed range.

        Args:
            amount: The requested raise amount.
            action: The available raise action to validate against.
            action_type: The action type string for error context.

        Returns:
            AvailableRaiseAction if valid, or ParseError if validation failed.
        """
        if amount < action.min_raise_amount.value:
            return ParseError.create(
                ParseErrorType.AMOUNT_BELOW_MIN,
                f"Raise amount {amount} is below minimum {action.min_raise_amount.value}",
                context={
                    "requested_amount": amount,
                    "min_raise_amount": action.min_raise_amount.value,
                    "max_raise_amount": action.max_raise_amount.value,
                    "action_type": action_type,
                },
            )
        if amount > action.max_raise_amount.value:
            return ParseError.create(
                ParseErrorType.AMOUNT_ABOVE_MAX,
                f"Raise amount {amount} exceeds maximum {action.max_raise_amount.value}",
                context={
                    "requested_amount": amount,
                    "min_raise_amount": action.min_raise_amount.value,
                    "max_raise_amount": action.max_raise_amount.value,
                    "action_type": action_type,
                },
            )
        return action

    def _validate(
        self,
        action_type: str,
        amount: int | None,
        available_actions: list[AvailableActions],
    ) -> AvailableActions | ParseError:
        """Internal: Validate action against available actions.

        Args:
            action_type: The normalized action type string.
            amount: Optional amount for bet/raise actions.
            available_actions: List of available actions to validate against.

        Returns:
            AvailableActions if valid, or ParseError if validation failed.
        """
        for action in available_actions:
            if action.action_type.value != action_type:
                continue

            # For actions without amounts, direct match
            match action:
                case (
                    AvailableFoldAction()
                    | AvailableCheckAction()
                    | AvailableCallAction()
                    | AvailableAllInAction()
                ):
                    return action
                case AvailableBetAction():
                    if amount is not None:
                        return self._validate_bet_amount(
                            amount, action, action_type
                        )
                    # Default to min bet when amount not specified
                    return action
                case AvailableRaiseAction():
                    if amount is not None:
                        return self._validate_raise_amount(
                            amount, action, action_type
                        )
                    # Default to min raise when amount not specified
                    return action

        # No matching action type found
        action_types = [a.action_type.value for a in available_actions]
        return ParseError.create(
            ParseErrorType.ACTION_NOT_AVAILABLE,
            f"Action '{action_type}' is not available. Available actions: {action_types}",
            context={
                "requested_action_type": action_type,
                "requested_amount": amount,
                "available_action_types": action_types,
            },
        )

    def _create(
        self,
        available: AvailableActions,
        requested_amount: int | None,
    ) -> Action:
        """Internal: Create Action domain object from AvailableAction.

        Args:
            available: The available action to create from.
            requested_amount: Optional requested amount (for bet/raise).

        Returns:
            Created Action object.

        Raises:
            ValueError: If action creation fails.
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
                # Use requested amount if valid, else min bet
                if requested_amount is not None:
                    amount = max(
                        available.min_bet_amount.value,
                        min(requested_amount, available.max_bet_amount.value),
                    )
                else:
                    amount = available.min_bet_amount.value
                return Action(
                    action_type=ActionType.BET,
                    amount=ChipAmount(amount),
                )
            case AvailableRaiseAction():
                # Use requested amount if valid, else min raise
                if requested_amount is not None:
                    amount = max(
                        available.min_raise_amount.value,
                        min(
                            requested_amount, available.max_raise_amount.value
                        ),
                    )
                else:
                    amount = available.min_raise_amount.value
                return Action(
                    action_type=ActionType.RAISE,
                    amount=ChipAmount(amount),
                )
            case _:
                raise ValueError(f"Unknown available action type: {available}")

    def parse(
        self,
        response_text: str,
        available_actions: list[AvailableActions],
    ) -> Action | ParseError:
        """Parse action from response text.

        Orchestrates extraction, validation, and creation.

        Args:
            response_text: The full LLM response text.
            available_actions: List of available actions to validate against.

        Returns:
            Action if parsing succeeded, or ParseError if it failed.
        """
        # Extract
        extracted = self._extract(response_text)
        if not extracted:
            return ParseError.create(
                ParseErrorType.NO_ACTION_FOUND,
                "Could not find valid ACTION in response. "
                "Expected format: ACTION: <fold|check|call|bet|raise|all_in> [amount]",
                context={
                    "response_snippet": (
                        response_text[:200]
                        if len(response_text) > 200
                        else response_text
                    ),
                },
            )

        action_type, amount = extracted

        # Validate
        available = self._validate(action_type, amount, available_actions)
        if isinstance(available, ParseError):
            return available

        # Create
        try:
            return self._create(available, amount)
        except Exception as e:
            return ParseError.create(
                ParseErrorType.INVALID_FORMAT,
                f"Failed to create action: {e}",
                context={
                    "action_type": action_type,
                    "amount": amount,
                    "exception": str(e),
                },
            )
