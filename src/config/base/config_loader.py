"""Base class for configuration loaders that don't use environment sections."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, TypeVar

import structlog

from src.config.utils.json_file_loader import JsonFileLoader

T = TypeVar("T")


class BaseConfigLoader(ABC, Generic[T]):
    """Base class for config loaders that don't need environment awareness.

    Provides:
    - JSON file loading with caching
    - Consistent error handling
    - Path validation

    Subclasses implement `_load_config()` to parse their specific config structure.
    """

    def __init__(
        self,
        config_path: Path,
        logger: structlog.BoundLogger,
        *,
        json_loader: JsonFileLoader | None = None,
    ) -> None:
        """Initialize base config loader.

        Args:
            config_path: Path to configuration file or directory.
            logger: Logger for error and info messages (required).
            json_loader: Optional JSON loader (for testing). Defaults to creating new one.
        """
        self._config_path: Path = config_path
        self._logger: structlog.BoundLogger = logger
        self._json_loader: JsonFileLoader = json_loader or JsonFileLoader(
            config_path=config_path, logger=logger
        )
        self._cached: T | None = None

    def load(self) -> T:
        """Load configuration, using cache if available.

        Returns:
            Configuration object of type T.

        Raise:
            ValueError: If config cannot be parsed.
            FileNotFoundError: If config file/directory does not exist.
        """
        if self._cached is not None:
            return self._cached

        self._cached = self._load_config()
        return self._cached

    @abstractmethod
    def _load_config(self) -> T:
        """Subclasses implement this to parse config.

        Returns:
            Configuration object of type T.

        Raises:
            ValueError: If config cannot be parsed.
        """
        raise NotImplementedError
