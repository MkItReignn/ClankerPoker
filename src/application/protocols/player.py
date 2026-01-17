"""Core generic protocols for action providers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

# Generic type variables for game-agnostic design
# Contravariant: used as input parameters in Protocol methods
TContext = TypeVar("TContext", contravariant=True)
TAvailableActions = TypeVar("TAvailableActions", contravariant=True)
# Covariant: used in return types
TAction = TypeVar("TAction", covariant=True)
TNarration = TypeVar("TNarration", covariant=True)


@dataclass(frozen=True, slots=True)
class PlayerConfig:
    """Configuration for a player's LLM behavior.

    This is game-agnostic configuration that controls how the LLM
    generates responses for this player.

    Attributes:
        player_id: Unique identifier for the player in the game.
        name: Display name for the player (used in prompts).
        personality: Optional personality description for system prompt generation.
        addon_prompt: Optional additional prompt text for customization.
        model_id: The LLM model identifier to use.
    """

    player_id: str
    name: str
    personality: str | None = None
    addon_prompt: str | None = None
    model_id: str

    def __post_init__(self) -> None:
        if not self.player_id:
            raise ValueError("player_id cannot be empty")
        if not self.name:
            raise ValueError("name cannot be empty")
        if not self.model_id:
            raise ValueError("model_id cannot be empty")


@dataclass(frozen=True, slots=True)
class ActionResponse(Generic[TAction, TNarration]):
    """Response from an action provider.

    Contains the chosen action and optional reasoning/narration.
    The narration is game-specific structured output for display.

    Attributes:
        action: The chosen action (game-specific type).
        reasoning: Optional internal reasoning from the LLM.
        narration: Optional structured narration for display (game-specific type).
    """

    action: TAction
    reasoning: str | None = None
    narration: TNarration | None = None


class AsyncActionProvider(Protocol[TContext, TAvailableActions, TAction, TNarration]):
    """Protocol for providers that generate actions based on game context.

    This is a game-agnostic protocol that can be implemented for any turn-based
    game. The type parameters allow full type safety for game-specific types.

    Type Parameters:
        TContext: The context type containing all information needed for a decision.
        TAvailableActions: The type representing available actions.
        TAction: The action type returned.
        TNarration: The narration type for structured output.
    """

    async def get_action(
        self,
        context: TContext,
        available_actions: TAvailableActions,
        config: PlayerConfig,
    ) -> ActionResponse[TAction, TNarration]:
        """Get an action for the current game state.

        Args:
            context: All information needed to make a decision.
            available_actions: The set of legal actions.
            config: Configuration for this player's behavior.

        Returns:
            ActionResponse containing the chosen action and optional narration.
        """
        ...
