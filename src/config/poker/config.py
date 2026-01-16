"""Poker game configuration data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.domain.models.llm_model import LlmModel

if TYPE_CHECKING:
    from src.application.protocols.player import PlayerConfig


@dataclass(frozen=True, slots=True)
class PokerPlayerConfig:
    """Configuration for a poker player.

    Defines how an LLM player behaves in poker games, including
    their model, system prompt, and optional personality traits.

    Attributes:
        player_id: Unique identifier for the player in the game.
        name: Display name for the player (used in prompts and history).
        system_prompt: System prompt for the LLM (personality, style, behavior).
        model_id: The LLM model to use for this player.
        personality: Optional poker-specific personality description.
    """

    player_id: str
    name: str
    system_prompt: str
    model_id: LlmModel
    personality: str | None = None

    def __post_init__(self) -> None:
        if not self.player_id:
            raise ValueError("player_id cannot be empty")
        if not self.name:
            raise ValueError("name cannot be empty")
        if not self.system_prompt:
            raise ValueError("system_prompt cannot be empty")

    def to_player_config(self) -> PlayerConfig:
        """Convert to generic PlayerConfig for use with action providers.

        Returns:
            PlayerConfig instance with model_id as string value.
        """
        from src.application.protocols.player import PlayerConfig

        return PlayerConfig(
            player_id=self.player_id,
            name=self.name,
            system_prompt=self.system_prompt,
            model_id=self.model_id.value,
        )


@dataclass(frozen=True, slots=True)
class PokerGameConfig:
    """Configuration for a poker game runner.

    Contains player configurations for all players in the game.
    Players without explicit configuration will need to be handled
    by the game runner with appropriate defaults.

    Attributes:
        player_configs: Configuration for each player, keyed by player_id.
    """

    player_configs: dict[str, PokerPlayerConfig] = field(default_factory=dict)
