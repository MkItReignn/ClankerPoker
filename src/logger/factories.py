"""Logger factory functions."""

from typing import Any

import structlog

from src.logger.config import configure_logging

_logging_initialized = False


def _ensure_logging_configured() -> None:
    """Ensure logging is configured before creating loggers.

    This provides a fallback console-only logging configuration when
    configure_logging() hasn't been called explicitly. For file logging,
    the application should call configure_logging(prefix=...) directly.
    """
    global _logging_initialized
    if not _logging_initialized:
        configure_logging()  # Console-only, no file logging
        _logging_initialized = True


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """Get a logger instance.

    Args:
        name: Logger name (typically __name__). If None, uses root logger.

    Returns:
        Bound logger instance.
    """
    _ensure_logging_configured()
    return structlog.get_logger(name)


def get_generic_logger(
    component: str, **context: Any
) -> structlog.BoundLogger:
    _ensure_logging_configured()
    return structlog.get_logger().bind(component=component, **context)
