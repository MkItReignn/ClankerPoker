"""Protocols for building decision context and formatting prompts."""

from typing import Protocol, TypeVar

# Generic type variables
# Contravariant: used in parameter positions (input)
# Covariant: used in return positions (output)
TGameState = TypeVar("TGameState", contravariant=True)
TContext = TypeVar("TContext", covariant=True)  # Return type in ContextBuilder
TAvailableActions = TypeVar("TAvailableActions", contravariant=True)
TRecord = TypeVar("TRecord", contravariant=True)
TContextInput = TypeVar(
    "TContextInput", contravariant=True
)  # Parameter in PromptFormatter
TPlayerInfo = TypeVar(
    "TPlayerInfo", contravariant=True
)  # Player info for prompt formatting (typically PlayerConfig)


class ContextBuilder(Protocol[TGameState, TContext, TRecord]):
    """Protocol for building decision context from game state.

    Transforms raw game state into a context object optimized for LLM consumption.
    The context should contain all information the LLM needs to make a decision,
    filtered to only what the current player can see.

    Type Parameters:
        TGameState: The raw game state type.
        TContext: The context type for LLM consumption.
        TRecord: The record type containing past game information.
    """

    def build_context(
        self,
        state: TGameState,
        player_id: str,
        record: TRecord | None = None,
    ) -> TContext:
        """Build a decision context for the specified player.

        Args:
            state: The current game state.
            player_id: The player who needs to make a decision.
            record: Optional game record for additional context.

        Returns:
            A context object containing all visible information for the player.
        """
        ...


class PromptFormatter(Protocol[TContextInput, TAvailableActions, TPlayerInfo]):
    """Protocol for formatting context into LLM prompts.

    Transforms structured context and available actions into both system
    and user prompts suitable for LLM consumption. Player-specific
    information is passed via a game-defined player info type.

    Type Parameters:
        TContextInput: The context type to format (input parameter).
        TAvailableActions: The available actions type to include in the prompt.
        TPlayerInfo: The player info type (game-specific dataclass).
    """

    def format_prompts(
        self,
        context: TContextInput,
        available_actions: TAvailableActions,
        player_info: TPlayerInfo,
    ) -> tuple[str, str]:
        """Format context and available actions into system and user prompts.

        Args:
            context: The decision context containing game state information.
            available_actions: The set of legal actions to present.
            player_info: Player-specific information (name, personality, etc.).

        Returns:
            Tuple of (system_prompt, user_prompt). The system prompt should
            include core instructions and player identity, with any player
            customization layered on top. The user prompt contains the
            current game state and decision context.
        """
        ...
