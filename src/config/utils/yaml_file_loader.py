"""Shared YAML file loading with caching and error handling."""

from pathlib import Path
from typing import Any, final

import structlog
import yaml

from src.config.utils.json_file_loader import DefaultFileReader, FileReader


@final
class YamlFileLoader:
    """Loads YAML files with caching and error handling."""

    def __init__(
        self,
        config_path: Path,
        logger: structlog.BoundLogger,
        *,
        file_reader: FileReader | None = None,
    ) -> None:
        """Initialize YAML file loader.

        Args:
            config_path: Path to YAML configuration file.
            logger: Logger for error and info messages.
            file_reader: Optional file reader implementation (for testing).
                Defaults to DefaultFileReader.
        """
        self._config_path = config_path
        self._logger = logger
        self._file_reader = file_reader or DefaultFileReader()
        self._cached: dict[str, Any] | None = None

    def load(self) -> dict[str, Any]:
        """Load entire YAML file.

        Returns:
            Parsed YAML as dictionary.

        Raises:
            FileNotFoundError: If config file does not exist.
            ValueError: If YAML is invalid or root is not a mapping/dict.
            RuntimeError: If file cannot be read.
        """
        if self._cached is not None:
            return self._cached

        if not self._file_reader.exists(self._config_path):
            self._logger.error(
                "config_file_not_found",
                config_path=str(self._config_path),
            )
            raise FileNotFoundError(
                f"Configuration file not found: {self._config_path}"
            )

        try:
            raw_text = self._file_reader.read_text(
                self._config_path, encoding="utf-8"
            )
            loaded_config = yaml.safe_load(raw_text)
        except yaml.YAMLError as e:
            self._logger.error(
                "config_invalid_yaml",
                config_path=str(self._config_path),
                error=str(e),
            )
            raise ValueError(f"Invalid YAML in config file: {e}") from e
        except Exception as e:
            self._logger.error(
                "config_load_failed",
                config_path=str(self._config_path),
                error=str(e),
            )
            raise RuntimeError(f"Failed to load config: {e}") from e

        if loaded_config is None:
            # Empty YAML file or only comments
            loaded_config = {}

        if not isinstance(loaded_config, dict):
            raise ValueError(
                "Config file must contain a YAML mapping (dictionary)"
            )

        self._cached = loaded_config
        self._logger.info(
            "config_loaded",
            config_path=str(self._config_path),
        )
        return self._cached

    def load_template(self, template_name: str) -> str:
        """Load a text template from a YAML file.

        This method is designed for loading template strings from YAML files.
        The YAML file should contain a mapping with template names as keys
        and template strings as values.

        Args:
            template_name: Key name of the template in the YAML file.

        Returns:
            Template content as string.

        Raises:
            FileNotFoundError: If config file does not exist.
            ValueError: If template_name is not found in the YAML file,
                or if the template value is not a string.
            RuntimeError: If file cannot be read.
        """
        config = self.load()

        if template_name not in config:
            self._logger.error(
                "template_not_found",
                template_name=template_name,
                config_path=str(self._config_path),
            )
            raise ValueError(
                f"Template '{template_name}' not found in {self._config_path}"
            )

        template_value = config[template_name]

        if not isinstance(template_value, str):
            raise ValueError(
                f"Template '{template_name}' must be a string, "
                f"got {type(template_value).__name__}"
            )

        return template_value
