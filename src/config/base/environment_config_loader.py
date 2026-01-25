"""Base class for environment-aware configuration loaders."""

from abc import abstractmethod
from pathlib import Path
from typing import TypeVar

import structlog

from src.config.base.config_loader import BaseConfigLoader
from src.config.utils.environment_resolver import (
    DefaultEnvironmentResolver,
    EnvironmentResolver,
)
from src.config.utils.json_file_loader import JsonFileLoader
from src.core.enums import ApplicationEnvironment

T = TypeVar("T")


class BaseEnvironmentConfigLoader(BaseConfigLoader[T]):
    """Base class for loaders that load environment-specific configs from JSON.

    This base class provides:
    - Environment resolution with dependency injection
    - JSON file loading with caching
    - Environment section extraction
    - Consistent error handling

    Subclasses implement `_load_config()` to parse their specific config structure.
    """

    def __init__(
        self,
        config_path: Path,
        logger: structlog.BoundLogger,
        *,
        environment: ApplicationEnvironment | None = None,
        environment_resolver: EnvironmentResolver | None = None,
        json_loader: JsonFileLoader | None = None,
    ) -> None:
        """Initialize base environment config loader.

        Args:
            config_path: Path to JSON configuration file.
            logger: Logger for error and info messages (required).
            environment: Application environment enum. If None, resolved from environment_resolver.
            environment_resolver: Optional environment resolver (for testing).
                Defaults to DefaultEnvironmentResolver.
            json_loader: Optional JSON loader (for testing). Defaults to creating new one.
        """
        super().__init__(
            config_path=config_path,
            logger=logger,
            json_loader=json_loader,
        )
        self._environment_resolver: EnvironmentResolver = (
            environment_resolver or DefaultEnvironmentResolver(logger=logger)
        )
        self._environment: ApplicationEnvironment = (
            environment or self._environment_resolver.resolve()
        )

    @property
    def environment(self) -> ApplicationEnvironment:
        """Current application environment enum."""
        return self._environment

    @abstractmethod
    def _load_config(self) -> T:
        """Subclasses implement this to parse config from JSON.

        Returns:
            Configuration object of type T.

        Raises:
            ValueError: If config cannot be parsed.
        """
        raise NotImplementedError

    def _get_environment_section(
        self,
        *,
        required: bool = True,
    ) -> dict[str, object] | None:
        """Get environment-specific section from JSON.

        Args:
            required: If True, raise error when environment section is missing.
                If False, return None when missing.

        Returns:
            Environment-specific config dictionary, or None if not found and required=False.

        Raises:
            ValueError: If environment section is missing and required=True,
                or if environment section is not a JSON object.
        """
        return self._json_loader.get_environment_section(
            self._environment, required=required
        )
