"""Poker prompt configuration loader.

Modular configuration system for poker prompts with separate methods
for extracting each component (system_prompt, user_prompt, retry_prompt).
"""

from __future__ import annotations

from pathlib import Path
from typing import final

import structlog

from src.config.poker.prompt.config import (PokerPromptConfig,
                                            ResponseGuidelines,
                                            RetryPromptComponents,
                                            SystemPromptComponents,
                                            UserPromptComponents)
from src.config.utils.type_extractors import ConfigTypeExtractor
from src.config.utils.yaml_file_loader import YamlFileLoader
from src.constants.config import POKER_PROMPTS_CONFIG_PATH
from src.logger.factories import get_generic_logger


@final
class PokerPromptConfigLoader:
    """Loads poker prompt configuration from YAML.

    Uses separate methods to extract each prompt component from the same file.
    Follows the same pattern as other config loaders with caching.
    """

    def __init__(
        self,
        config_path: Path | None = None,
        logger: structlog.BoundLogger | None = None,
        *,
        yaml_loader: YamlFileLoader | None = None,
    ) -> None:
        """Initialize poker prompt config loader.

        Args:
            config_path: Path to prompts.yaml file. Defaults to POKER_PROMPTS_CONFIG_PATH.
            logger: Optional logger. Defaults to creating one.
            yaml_loader: Optional YAML loader (for testing).
        """
        resolved_path = config_path or POKER_PROMPTS_CONFIG_PATH
        resolved_logger = logger or get_generic_logger(__name__.removeprefix("src."))
        self._yaml_loader = yaml_loader or YamlFileLoader(
            config_path=resolved_path, logger=resolved_logger
        )
        self._logger = resolved_logger
        self._cached: PokerPromptConfig | None = None

    def _load_system_prompt_components(
        self,
        payload: dict[str, object],
    ) -> SystemPromptComponents:
        """Extract system prompt components from YAML payload.

        Args:
            payload: Root YAML payload dictionary.

        Returns:
            SystemPromptComponents object.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        extractor = ConfigTypeExtractor(logger=self._logger)

        system_prompt_raw = extractor.get_required_dict(payload, "system_prompt", context="root")

        identity = extractor.get_required_string(
            system_prompt_raw, "identity", context="system_prompt"
        )
        context_format_guide = extractor.get_required_string(
            system_prompt_raw, "context_format_guide", context="system_prompt"
        )
        history_notation = extractor.get_required_string(
            system_prompt_raw, "history_notation", context="system_prompt"
        )
        decision_framework = extractor.get_required_string(
            system_prompt_raw, "decision_framework", context="system_prompt"
        )
        personality_section = extractor.get_required_string(
            system_prompt_raw, "personality_section", context="system_prompt"
        )
        addon_section = extractor.get_required_string(
            system_prompt_raw, "addon_section", context="system_prompt"
        )

        return SystemPromptComponents(
            identity=identity,
            context_format_guide=context_format_guide,
            history_notation=history_notation,
            decision_framework=decision_framework,
            personality_section=personality_section,
            addon_section=addon_section,
        )

    def _load_user_prompt_components(
        self,
        payload: dict[str, object],
    ) -> UserPromptComponents:
        """Extract user prompt components from YAML payload.

        Args:
            payload: Root YAML payload dictionary.

        Returns:
            UserPromptComponents object.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        extractor = ConfigTypeExtractor(logger=self._logger)

        user_prompt_raw = extractor.get_required_dict(payload, "user_prompt", context="root")

        response_format = extractor.get_required_string(
            user_prompt_raw, "response_format", context="user_prompt"
        )

        # Extract response_guidelines
        response_guidelines_raw = extractor.get_required_dict(
            user_prompt_raw, "response_guidelines", context="user_prompt"
        )

        thought_process_guidelines = extractor.get_required_string(
            response_guidelines_raw, "thought_process_guidelines", context="response_guidelines"
        )
        action_guidelines = extractor.get_required_string(
            response_guidelines_raw, "action_guidelines", context="response_guidelines"
        )

        response_guidelines = ResponseGuidelines(
            thought_process_guidelines=thought_process_guidelines,
            action_guidelines=action_guidelines,
        )

        return UserPromptComponents(
            response_format=response_format,
            response_guidelines=response_guidelines,
        )

    def _load_retry_prompt_components(
        self,
        payload: dict[str, object],
    ) -> RetryPromptComponents:
        """Extract retry prompt components from YAML payload.

        Args:
            payload: Root YAML payload dictionary.

        Returns:
            RetryPromptComponents object.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        extractor = ConfigTypeExtractor(logger=self._logger)

        retry_prompt_raw = extractor.get_required_dict(payload, "retry_prompt", context="root")

        header = extractor.get_required_string(retry_prompt_raw, "header", context="retry_prompt")
        error_section = extractor.get_required_string(
            retry_prompt_raw, "error_section", context="retry_prompt"
        )
        response_section = extractor.get_required_string(
            retry_prompt_raw, "response_section", context="retry_prompt"
        )
        footer = extractor.get_required_string(retry_prompt_raw, "footer", context="retry_prompt")

        return RetryPromptComponents(
            header=header,
            error_section=error_section,
            response_section=response_section,
            footer=footer,
        )

    def load(self) -> PokerPromptConfig:
        """Load configuration, using cache if available.

        Returns:
            PokerPromptConfig object.

        Raises:
            FileNotFoundError: If config file does not exist.
            ValueError: If config cannot be parsed or required fields are missing.
        """
        if self._cached is not None:
            return self._cached

        payload = self._yaml_loader.load()

        # Extract each component using dedicated methods
        system_prompt = self._load_system_prompt_components(payload)
        user_prompt = self._load_user_prompt_components(payload)
        retry_prompt = self._load_retry_prompt_components(payload)

        self._cached = PokerPromptConfig(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            retry_prompt=retry_prompt,
        )

        self._logger.info("poker_prompt_config_loaded")
        return self._cached
