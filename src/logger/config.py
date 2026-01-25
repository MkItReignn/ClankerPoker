"""Centralized structlog + stdlib logging configuration for ClankerPoker.

This module provides production-ready logging configuration using structlog
with proper integration with Python's standard library logging.

Features:
- Root logger at DEBUG
- Console handler level configurable (DEBUG in verbose mode, ERROR otherwise)
- Structlog integrated with stdlib via ProcessorFormatter
- Development-friendly console output or JSON for production
"""

import logging
import logging.handlers
import sys
from datetime import UTC, datetime
from pathlib import Path

import structlog
from structlog.types import EventDict

from src.logger.shared import suppress_third_party_libraries

_logging_configured = False
_file_handler: logging.Handler | None = None


def _ensure_dict(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Ensure event_dict is a dict (for foreign pre_chain)."""
    if not isinstance(event_dict, dict):
        return {"event": str(event_dict)}
    return event_dict


def _configure_root_logger() -> logging.Logger:
    """Set up the root logger with a clean handler set."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()
    return root_logger


def _create_formatter(
    dev_mode: bool = True,
) -> structlog.stdlib.ProcessorFormatter:
    """Create ProcessorFormatter for console or file handler.

    Args:
        dev_mode: If True, use development-friendly console output.
                 If False, use JSON output for production.
    """
    if dev_mode:
        renderer = structlog.dev.ConsoleRenderer(colors=True, sort_keys=False)
    else:
        renderer = structlog.processors.JSONRenderer()

    return structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=[
            _ensure_dict,
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ],
    )


def _configure_structlog_processors() -> None:
    """Configure structlog to emit records compatible with ProcessorFormatter."""
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def configure_logging(
    prefix: str | None = None,
    dev_mode: bool = True,
    verbose: bool = False,
) -> Path | None:
    """Configure structlog + stdlib logging for production/dev.

    Args:
        prefix: Prefix for log filename. If provided, logs will be written to a
               file named {prefix}_{timestamp}.log in the logs/ directory.
               If None, only console logging is enabled (no file logging).
        dev_mode: If True, use development-friendly console output.
                 If False, use JSON output for production.
        verbose: If True, set console handler to DEBUG level to show all logs.
                If False, set console handler to ERROR level (only errors shown).

    Returns:
        Path to the log file if prefix is provided, None otherwise.
    """
    global _logging_configured, _file_handler

    if _logging_configured:
        # Remove existing file handler if reconfiguring
        if _file_handler is not None:
            root_logger = logging.getLogger()
            root_logger.removeHandler(_file_handler)
            _file_handler.close()
            _file_handler = None
        structlog.reset_defaults()

    root_logger = _configure_root_logger()
    suppress_third_party_libraries()

    formatter = _create_formatter(dev_mode=dev_mode)

    # Add console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.DEBUG if verbose else logging.ERROR)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add file handler if prefix is provided
    log_file: Path | None = None
    if prefix is not None:
        log_file = _create_file_handler(prefix, formatter, verbose)
        if _file_handler is not None:
            root_logger.addHandler(_file_handler)

    _configure_structlog_processors()

    _logging_configured = True

    # Print log destination information if file logging is enabled
    if log_file is not None:
        log_file_abs = log_file.resolve()
        print(
            f"\n📋 Logging started: All logs are being written to {log_file_abs}",
            file=sys.stderr,
        )
        print(
            f"🔍 To follow logs in real-time: tail -F {log_file_abs}\n",
            file=sys.stderr,
        )

    return log_file


def _create_file_handler(
    prefix: str,
    formatter: logging.Formatter,
    verbose: bool,
) -> Path:
    """Create a file handler for logging to a file with prefix and timestamp.

    Args:
        prefix: The prefix to include in the filename.
        formatter: The formatter to use for the file handler.
        verbose: Whether verbose logging is enabled (affects log level).

    Returns:
        Path to the created log file.

    Raises:
        RuntimeError: If file creation fails.
    """
    global _file_handler

    try:
        # Create logs directory
        project_root = Path(__file__).parent.parent.parent
        logs_dir = project_root / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename: {prefix}_{timestamp}.log
        # Format: YYYYMMDDTHHMMSSZ (ISO 8601 without separators, UTC)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        # Sanitize prefix for filename (remove invalid characters)
        safe_prefix = "".join(c for c in prefix if c.isalnum() or c in "-_")
        log_filename = f"{safe_prefix}_{timestamp}.log"
        log_file = logs_dir / log_filename

        # Create rotating file handler (10MB max, 5 backups)
        _file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        _file_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
        _file_handler.setFormatter(formatter)

        return log_file
    except Exception as e:
        raise RuntimeError(
            f"Failed to create log file with prefix={prefix}: {e}"
        ) from e


def shutdown_logging() -> None:
    """Gracefully shutdown logging."""
    global _logging_configured, _file_handler

    if _file_handler is not None:
        root_logger = logging.getLogger()
        root_logger.removeHandler(_file_handler)
        _file_handler.close()
        _file_handler = None

    _logging_configured = False
    structlog.reset_defaults()
