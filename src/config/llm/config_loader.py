"""LLM configuration loader.

Loads OpenRouter client configuration from JSON files.
Configuration files are located at the project root in config/llm/.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, final, override

import structlog

from src.config.base.config_loader import BaseConfigLoader
from src.config.llm.config import OpenRouterConfig
from src.config.utils.type_extractors import ConfigTypeExtractor
from src.constants.config import LLM_CONFIG_PATH
from src.logger.factories import get_generic_logger


@final
class OpenRouterConfigLoader(BaseConfigLoader[OpenRouterConfig]):
    """Loads OpenRouter client configuration from JSON."""

    def __init__(
        self,
        config_path: Path | None = None,
        logger: structlog.BoundLogger | None = None,
        *,
        json_loader: Any = None,
    ) -> None:
        """Initialize OpenRouter config loader.

        Args:
            config_path: Path to config file. Defaults to LLM_CONFIG_PATH.
            logger: Optional logger. Defaults to creating one.
            json_loader: Optional JSON loader (for testing).
        """
        resolved_path = config_path or LLM_CONFIG_PATH
        resolved_logger = logger or get_generic_logger(__name__.removeprefix("src."))
        super().__init__(
            config_path=resolved_path,
            logger=resolved_logger,
            json_loader=json_loader,
        )

    @override
    def _load_config(self) -> OpenRouterConfig:
        """Load OpenRouter configuration from JSON.

        Returns:
            OpenRouterConfig object.

        Raises:
            FileNotFoundError: If config file does not exist.
            ValueError: If config cannot be parsed or required fields are missing.
        """
        payload = self._json_loader.load()
        extractor = ConfigTypeExtractor(logger=self._logger)

        # Extract required api_key
        api_key = extractor.get_required_string(payload, "api_key", context="root")

        # Extract optional fields with defaults
        base_url = extractor.get_string_with_default(
            payload,
            "base_url",
            default="https://openrouter.ai/api/v1",
            context="root",
        )

        timeout = extractor.get_float_with_default(
            payload,
            "timeout",
            default=60.0,
            context="root",
        )

        config = OpenRouterConfig(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )

        self._logger.info("openrouter_config_loaded")
        return config
