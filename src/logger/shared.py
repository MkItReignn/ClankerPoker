"""Shared logging helpers and configuration constants."""

import logging

# Libraries we always dial down to WARNING to reduce noise.
ALWAYS_SUPPRESSED_THIRD_PARTY_LOGS: list[str] = [
    "httpx",
    "asyncio",
    "aiohttp",
    "urllib3",
]

# Mapping from logical name to actual logger names used by those libraries.
THIRD_PARTY_LOGGER_MAP: dict[str, list[str]] = {
    "httpx": ["httpx"],
    "aiohttp": ["aiohttp"],
    "urllib3": ["urllib3"],
    "asyncio": ["asyncio"],
}


def suppress_third_party_libraries() -> None:
    """Apply WARNING level to noisy third-party loggers.

    Safe to call multiple times.
    """
    for lib_name in ALWAYS_SUPPRESSED_THIRD_PARTY_LOGS:
        for logger_name in THIRD_PARTY_LOGGER_MAP.get(lib_name, []):
            logging.getLogger(logger_name).setLevel(logging.WARNING)
