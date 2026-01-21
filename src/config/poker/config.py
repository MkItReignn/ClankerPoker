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
    their model, optional personality, and optional addon prompt.

    Attributes:
        player_id: Unique identifier for the player in the game.
        name: Display name for the player (used in prompts and history).
        model_id: The LLM model to use for this player.
        personality: Optional personality description used in system prompt generation.
        addon_prompt: Optional additional prompt text for future customization.
    """

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

    def to_player_config(self) -> PlayerConfig:
        """Convert to generic PlayerConfig for use with action providers.

        Returns:
            PlayerConfig instance with all player configuration including model_id.
        """
        from src.application.protocols.player import PlayerConfig

        return PlayerConfig(
            player_id=self.player_id,
            name=self.name,
            model_id=self.model_id,
            personality=self.personality,
            addon_prompt=self.addon_prompt,
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
