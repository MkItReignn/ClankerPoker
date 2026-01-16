"""Abstraction for environment resolution."""

from typing import Protocol, final

import structlog

from src.core.enums import ApplicationEnvironment
from src.utils.environment import load_environment_name


class EnvironmentResolver(Protocol):
    """Protocol for resolving current application environment."""

    def resolve(self) -> ApplicationEnvironment:
        """Resolve current application environment.

        Returns:
            ApplicationEnvironment enum (e.g., ApplicationEnvironment.DEVELOPMENT, ApplicationEnvironment.PRODUCTION).
        """
        ...


@final
class DefaultEnvironmentResolver:
    """Default environment resolver using load_environment_name()."""

    def __init__(self, logger: structlog.BoundLogger | None = None) -> None:
        """Initialize environment resolver.

        Args:
            logger: Optional logger for environment resolution logging.
                If not provided, load_environment_name will use its module logger.
        """
        self._logger = logger

    def resolve(self) -> ApplicationEnvironment:
        return load_environment_name(logger=self._logger)
