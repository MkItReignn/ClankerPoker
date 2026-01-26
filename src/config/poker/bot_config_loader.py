"""Bot player configuration loader.

Loads bot player configuration from JSON files.
Configuration files are located at the project root in config/poker/.
"""

from pathlib import Path
from typing import Any, final, override

import structlog

from src.config.base.config_loader import BaseConfigLoader
from src.config.poker.bot_config import (
    BotPokerGameConfig,
    BotPokerPlayerConfig,
)
from src.config.poker.bot_personality import BotPersonality
from src.config.utils.type_extractors import ConfigTypeExtractor
from src.config.file_paths import BOT_PLAYERS_CONFIG_PATH
from src.logger.factories import get_generic_logger


@final
class BotPokerGameConfigLoader(BaseConfigLoader[BotPokerGameConfig]):
    """Loads bot poker game configuration from JSON."""

    def __init__(
        self,
        config_path: Path | None = None,
        logger: structlog.BoundLogger | None = None,
        *,
        json_loader: Any = None,
    ) -> None:
        """Initialize bot poker game config loader.

        Args:
            config_path: Path to config file. Defaults to BOT_PLAYERS_CONFIG_PATH.
            logger: Optional logger. Defaults to creating one.
            json_loader: Optional JSON loader (for testing).
        """
        resolved_path = config_path or BOT_PLAYERS_CONFIG_PATH
        resolved_logger = logger or get_generic_logger(
            __name__.removeprefix("src.")
        )
        super().__init__(
            config_path=resolved_path,
            logger=resolved_logger,
            json_loader=json_loader,
        )

    @override
    def _load_config(self) -> BotPokerGameConfig:
        """Load bot poker game configuration from JSON.

        Returns:
            BotPokerGameConfig object.

        Raises:
            FileNotFoundError: If config file does not exist.
            ValueError: If config cannot be parsed or required fields are missing.
        """
        payload = self._json_loader.load()
        extractor = ConfigTypeExtractor(logger=self._logger)

        player_configs_raw = extractor.get_dict_or_default(
            payload, "player_configs", default={}, context="root"
        )

        player_configs: dict[str, BotPokerPlayerConfig] = {}
        for player_id, player_data in player_configs_raw.items():
            if not isinstance(player_data, dict):
                raise ValueError(
                    f"player_configs['{player_id}'] must be a JSON object, "
                    f"got {type(player_data).__name__}"
                )

            name = extractor.get_required_string(
                player_data, "name", context=f"player_configs['{player_id}']"
            )
            personality_str = extractor.get_required_string(
                player_data,
                "personality",
                context=f"player_configs['{player_id}']",
            )

            try:
                personality = BotPersonality(personality_str)
            except ValueError:
                valid_values = [e.value for e in BotPersonality]
                raise ValueError(
                    f"Invalid personality for player '{player_id}': {personality_str}. "
                    f"Valid values: {valid_values}"
                ) from None

            player_config = BotPokerPlayerConfig(
                player_id=player_id,
                name=name,
                personality=personality,
            )
            player_configs[player_id] = player_config

        config = BotPokerGameConfig(player_configs=player_configs)
        self._logger.info(
            "bot_poker_game_config_loaded",
            num_players=len(config.player_configs),
        )
        return config
