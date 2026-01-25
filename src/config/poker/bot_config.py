"""Bot player configuration data structures."""

from dataclasses import dataclass, field

from src.config.poker.bot_personality import BotPersonality


@dataclass(frozen=True, slots=True)
class BotPokerPlayerConfig:
    """Configuration for a bot poker player.

    Defines how a bot player behaves in poker games.

    Attributes:
        player_id: Unique identifier for the player in the game.
        name: Display name for the player.
        personality: Bot personality that determines playing style.
    """

    player_id: str
    name: str
    personality: BotPersonality

    def __post_init__(self) -> None:
        if not self.player_id:
            raise ValueError("player_id cannot be empty")
        if not self.name:
            raise ValueError("name cannot be empty")


@dataclass(frozen=True, slots=True)
class BotPokerGameConfig:
    """Configuration for a bot poker game.

    Contains player configurations for all bot players in the game.

    Attributes:
        player_configs: Configuration for each player, keyed by player_id.
    """

    player_configs: dict[str, BotPokerPlayerConfig] = field(
        default_factory=dict
    )
