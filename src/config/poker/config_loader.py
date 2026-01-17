"""Poker configuration loader.

Loads poker game configuration from JSON files.
Configuration files are located at the project root in config/poker/.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, final, override

import structlog

from src.config.base.config_loader import BaseConfigLoader
from src.config.poker.config import PokerGameConfig, PokerPlayerConfig
from src.config.utils.type_extractors import ConfigTypeExtractor
from src.constants.config import POKER_CONFIG_PATH
from src.domain.models.llm_model import LlmModel
from src.logger.factories import get_generic_logger


@final
class PokerGameConfigLoader(BaseConfigLoader[PokerGameConfig]):
    """Loads poker game configuration from JSON."""

    def __init__(
        self,
        config_path: Path | None = None,
        logger: structlog.BoundLogger | None = None,
        *,
        json_loader: Any = None,
    ) -> None:
        """Initialize poker game config loader.

        Args:
            config_path: Path to config file. Defaults to POKER_CONFIG_PATH.
            logger: Optional logger. Defaults to creating one.
            json_loader: Optional JSON loader (for testing).
        """
        resolved_path = config_path or POKER_CONFIG_PATH
        resolved_logger = logger or get_generic_logger(__name__.removeprefix("src."))
        super().__init__(
            config_path=resolved_path,
            logger=resolved_logger,
            json_loader=json_loader,
        )

    @override
    def _load_config(self) -> PokerGameConfig:
        """Load poker game configuration from JSON.

        Returns:
            PokerGameConfig object.

        Raises:
            FileNotFoundError: If config file does not exist.
            ValueError: If config cannot be parsed or required fields are missing.
        """
        payload = self._json_loader.load()
        extractor = ConfigTypeExtractor(logger=self._logger)

        player_configs_raw = extractor.get_dict_or_default(
            payload, "player_configs", default={}, context="root"
        )

        player_configs: dict[str, PokerPlayerConfig] = {}
        for player_id, player_data in player_configs_raw.items():
            if not isinstance(player_data, dict):
                raise ValueError(
                    f"player_configs['{player_id}'] must be a JSON object, "
                    f"got {type(player_data).__name__}"
                )

            name = extractor.get_required_string(
                player_data, "name", context=f"player_configs['{player_id}']"
            )
            model_id_str = extractor.get_required_string(
                player_data, "model_id", context=f"player_configs['{player_id}']"
            )

            try:
                model_id = LlmModel(model_id_str)
            except ValueError:
                valid_values = [e.value for e in LlmModel]
                raise ValueError(
                    f"Invalid model_id for player '{player_id}': {model_id_str}. "
                    f"Valid values: {valid_values}"
                ) from None

            personality = extractor.get_str_or_none(
                player_data, "personality", context=f"player_configs['{player_id}']"
            )
            addon_prompt = extractor.get_str_or_none(
                player_data, "addon_prompt", context=f"player_configs['{player_id}']"
            )

            player_config = PokerPlayerConfig(
                player_id=player_id,
                name=name,
                model_id=model_id,
                personality=personality,
                addon_prompt=addon_prompt,
            )
            player_configs[player_id] = player_config

        config = PokerGameConfig(player_configs=player_configs)
        self._logger.info(
            "poker_game_config_loaded",
            num_players=len(config.player_configs),
        )
        return config
