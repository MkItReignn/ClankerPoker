"""
Core enums used across the application.

This module provides the single source of truth for:
- Environment types
"""

from enum import Enum


class ApplicationEnvironment(str, Enum):
    """Where the ClankerPoker application is running.

    Controls application-level concerns:
    - Database configuration (which database to connect to)
    - Logging levels and output destinations
    - Feature flags and application behavior
    """

    PRODUCTION = "production"
    DEVELOPMENT = "development"
    TEST = "test"
