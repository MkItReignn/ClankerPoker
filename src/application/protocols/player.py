"""Core generic protocols for action providers."""

from dataclasses import dataclass
from typing import Protocol, Self, TypeVar

from src.application.protocols.response import ActionResponse
from src.domain.models.llm_model import LlmModel

# Generic type variables for game-agnostic design
# Contravariant: used only as input parameters in Protocol methods
TContext = TypeVar("TContext", contravariant=True)
TAvailableActions = TypeVar("TAvailableActions", contravariant=True)
# Invariant: used in ActionResponse which stores them as fields
TAction = TypeVar("TAction")
TNarration = TypeVar("TNarration")

# Re-export for backwards compatibility
# TODO: Remove this backwards compatability
__all__ = ["ActionResponse", "AsyncActionProvider", "PlayerConfig"]


@dataclass(frozen=True, slots=True)
class PlayerConfig:
    """Configuration for a player's LLM behavior."""

    player_id: str
    name: str
    model_id: LlmModel
    personality: str | None = None
    addon_prompt: str | None = None

    def __post_init__(self) -> None:
        if not self.player_id:
            raise ValueError("player_id cannot be empty")
        if not self.name:
            raise ValueError("name cannot be empty")


class AsyncActionProvider(
    Protocol[TContext, TAvailableActions, TAction, TNarration]
):
    """Protocol for providers that generate actions based on game context.

    This is a game-agnostic protocol that can be implemented for any turn-based
    game. The type parameters allow full type safety for game-specific types.

    Type Parameters:
        TContext: The context type containing all information needed for a decision.
        TAvailableActions: The type representing available actions.
        TAction: The action type returned.
        TNarration: The narration type for structured output.
    """

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None: ...

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
            config: Configuration for this player's behavior (includes model_id).

        Returns:
            ActionResponse containing the chosen action and optional narration.
        """
        ...
