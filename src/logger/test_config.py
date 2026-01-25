"""Minimal, pytest-friendly structlog + logging configuration for tests.

This module provides a simpler logging setup designed specifically for test
environments. It avoids the complexity of production logging:

- No QueueListener
- No ProcessorFormatter / wrap_for_formatter
- No custom transports
- Does NOT touch stdlib logging handlers (pytest owns those)
- Only configures structlog to emit JSON strings
- Logs are plain strings (JSON) so caplog can assert easily

This decouples test logging from production logging, eliminating the pain
points of trying to reuse the full production stack in tests.

IMPORTANT: This config does NOT modify stdlib logging handlers or levels.
Pytest's logging plugin and caplog manage stdlib logging. We only configure
structlog to emit JSON strings via stdlib logging.
"""

import structlog

from src.logger.shared import suppress_third_party_libraries


def configure_test_logging() -> None:
    """Minimal, pytest-friendly structlog config.

    IMPORTANT: does NOT touch stdlib logging handlers or levels.
    Pytest owns logging; we only configure structlog to emit JSON strings.

    This configuration:
    - Only configures structlog (does not touch stdlib logging)
    - Configures structlog to render JSON strings
    - Suppresses third-party library noise
    - Lets pytest's logging plugin + caplog handle stdlib logging

    No queues, no custom formatters, no stdlib manipulation - just structlog
    → stdlib → pytest capture.
    """
    # Do NOT clear or modify root handlers!
    # Do NOT add your own handlers!
    # Pytest's logging plugin + caplog will handle stdlib logging.

    # Suppress third-party library noise (same as production)
    suppress_third_party_libraries()

    # Reset structlog
    structlog.reset_defaults()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            # Last processor: turn event dict into JSON string
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
