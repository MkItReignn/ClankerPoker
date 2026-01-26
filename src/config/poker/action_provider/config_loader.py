"""Action provider configuration loader.

Loads action provider configuration from JSON files.
"""

from pathlib import Path
from typing import Any, final, override

import structlog

from src.config.base.config_loader import BaseConfigLoader
from src.config.poker.action_provider.config import ActionProviderConfig
from src.config.utils.type_extractors import ConfigTypeExtractor
from src.config.file_paths import ACTION_PROVIDER_CONFIG_PATH
from src.logger.factories import get_generic_logger


@final
class ActionProviderConfigLoader(BaseConfigLoader[ActionProviderConfig]):
    """Loads action provider configuration from JSON."""

    def __init__(
        self,
        config_path: Path | None = None,
        logger: structlog.BoundLogger | None = None,
        *,
        json_loader: Any = None,
    ) -> None:
        """Initialize action provider config loader.

        Args:
            config_path: Path to config file. Defaults to ACTION_PROVIDER_CONFIG_PATH.
            logger: Optional logger. Defaults to creating one.
            json_loader: Optional JSON loader (for testing).
        """
        resolved_path = config_path or ACTION_PROVIDER_CONFIG_PATH
        resolved_logger = logger or get_generic_logger(
            __name__.removeprefix("src.")
        )
        super().__init__(
            config_path=resolved_path,
            logger=resolved_logger,
            json_loader=json_loader,
        )

    @override
    def _load_config(self) -> ActionProviderConfig:
        """Load action provider configuration from JSON.

        Returns:
            ActionProviderConfig object.

        Raises:
            FileNotFoundError: If config file does not exist.
            ValueError: If config cannot be parsed or required fields are missing.
        """
        payload = self._json_loader.load()
        extractor = ConfigTypeExtractor(logger=self._logger)

        max_retries = extractor.get_required_int(
            payload, "max_retries", context="root"
        )
        temperature = extractor.get_required_float(
            payload, "temperature", context="root"
        )
        max_output_tokens = extractor.get_required_int(
            payload, "max_output_tokens", context="root"
        )

        config = ActionProviderConfig(
            max_retries=max_retries,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

        self._logger.info("action_provider_config_loaded")
        return config
