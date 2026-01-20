"""Structured logging package for ClankerPoker.

This package provides centralized logging configuration using structlog,
with domain-specific logger factories for different components.

Public API:
    - configure_logging(): Initialize structlog configuration
    - shutdown_logging(): Gracefully shutdown logging listener
    - get_logger(): Get logger instance
"""

from src.logger.config import configure_logging, shutdown_logging
from src.logger.factories import get_logger

__all__ = [
    "configure_logging",
    "shutdown_logging",
    "get_logger",
]
