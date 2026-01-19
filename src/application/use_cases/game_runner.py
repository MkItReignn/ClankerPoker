"""Abstract game runner for orchestrating turn-based games."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar
from collections.abc import Awaitable, Callable

from src.application.protocols.player import ActionResponse, PlayerConfig

# Generic type variables
TGameState = TypeVar("TGameState")
TContext = TypeVar("TContext")
TAvailableActions = TypeVar("TAvailableActions")
TAction = TypeVar("TAction")
TNarration = TypeVar("TNarration")
TEvent = TypeVar("TEvent")


@dataclass(frozen=True, slots=True)
class TurnResult(Generic[TGameState, TAction, TNarration, TEvent]):
    """Result of executing a single turn.

    Attributes:
        state: The game state after the turn.
        player_id: The player who acted.
        action: The action that was taken.
        narration: Optional narration from the action.
        events: Events generated during the turn.
    """

    state: TGameState
    player_id: str
    action: TAction
    narration: TNarration | None
    events: tuple[TEvent, ...] = ()


# Type alias for action provider callable
ActionProviderFn = Callable[
    [TContext, TAvailableActions, PlayerConfig],
    Awaitable[ActionResponse[TAction, TNarration]],
]


class GameRunner(
    ABC,
    Generic[TGameState, TContext, TAvailableActions, TAction, TNarration, TEvent],
):
    """Abstract base class for game runners.

    Orchestrates the game loop by:
    1. Getting the current player
    2. Building decision context
    3. Getting available actions
    4. Requesting an action from the provider
    5. Applying the action to the game state

    Subclasses implement game-specific logic for context building,
    action calculation, and state transitions.
    """

    def __init__(self) -> None:
        """Initialize the game runner with a logger."""
        self._logger = logging.getLogger(__name__)

    @abstractmethod
    def get_current_player_id(self, state: TGameState) -> str | None:
        """Get the ID of the player who needs to act.

        Args:
            state: The current game state.

        Returns:
            The player ID, or None if no player needs to act.
        """
        ...

    @abstractmethod
    def get_player_config(self, state: TGameState, player_id: str) -> PlayerConfig:
        """Get the configuration for a player.

        Args:
            state: The current game state.
            player_id: The player ID.

        Returns:
            The player's configuration.
        """
        ...

    @abstractmethod
    def build_context(self, state: TGameState, player_id: str) -> TContext:
        """Build decision context for a player.

        Args:
            state: The current game state.
            player_id: The player who needs to decide.

        Returns:
            The decision context.
        """
        ...

    @abstractmethod
    def get_available_actions(
        self,
        state: TGameState,
        player_id: str,
    ) -> TAvailableActions:
        """Get available actions for a player.

        Args:
            state: The current game state.
            player_id: The player who needs to decide.

        Returns:
            The available actions.
        """
        ...

    @abstractmethod
    def apply_action(
        self,
        state: TGameState,
        player_id: str,
        action: TAction,
        narration: TNarration | None = None,
    ) -> TurnResult[TGameState, TAction, TNarration, TEvent]:
        """Apply an action to the game state.

        Args:
            state: The current game state.
            player_id: The player taking the action.
            action: The action to apply.
            narration: Optional narration from the action.

        Returns:
            TurnResult with updated state and events.
        """
        ...

    @abstractmethod
    def is_game_over(self, state: TGameState) -> bool:
        """Check if the game is over.

        Args:
            state: The current game state.

        Returns:
            True if the game is over.
        """
        ...

    @abstractmethod
    def advance_game_phase(self, state: TGameState) -> TGameState:
        """Advance the game to the next phase if needed.

        Called when no player needs to act to handle
        phase transitions (e.g., dealing cards, starting new rounds).

        Args:
            state: The current game state.

        Returns:
            The updated game state.
        """
        ...

    async def run_turn(
        self,
        state: TGameState,
        action_provider: ActionProviderFn[TContext, TAvailableActions, TAction, TNarration],
    ) -> TurnResult[TGameState, TAction, TNarration, TEvent] | None:
        """Run a single turn of the game.

        Args:
            state: The current game state.
            action_provider: Function to get actions from.

        Returns:
            TurnResult if a turn was executed, None if no player to act.
        """
        player_id: str | None = self.get_current_player_id(state)
        if player_id is None:
            return None

        config: PlayerConfig = self.get_player_config(state, player_id)
        context = self.build_context(state, player_id)
        available_actions = self.get_available_actions(state, player_id)

        self._logger.debug(f"Player {player_id} needs to act")

        response = await action_provider(context, available_actions, config)

        self._logger.debug(f"Player {player_id} chose action: {response.action}")

        result = self.apply_action(
            state,
            player_id,
            response.action,
            response.narration,
        )

        return result

    async def run_game(
        self,
        initial_state: TGameState,
        action_provider: ActionProviderFn[TContext, TAvailableActions, TAction, TNarration],
        on_turn: (
            Callable[[TurnResult[TGameState, TAction, TNarration, TEvent]], None] | None
        ) = None,
        max_turns: int | None = None,
    ) -> TGameState:
        """Run the game until completion.

        Args:
            initial_state: The starting game state.
            action_provider: Function to get actions from.
            on_turn: Optional callback invoked after each turn.
            max_turns: Optional maximum number of turns (for safety).

        Returns:
            The final game state.
        """
        state = initial_state
        turn_count = 0

        while not self.is_game_over(state):
            # Check turn limit
            if max_turns is not None and turn_count >= max_turns:
                self._logger.warning(f"Reached max turns ({max_turns}), stopping game")
                break

            # Try to run a turn
            result = await self.run_turn(state, action_provider)

            if result is not None:
                state = result.state
                turn_count += 1

                if on_turn is not None:
                    on_turn(result)
            else:
                # No player to act, advance game phase
                state = self.advance_game_phase(state)

        self._logger.info(f"Game completed after {turn_count} turns")
        return state
