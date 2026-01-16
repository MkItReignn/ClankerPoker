"""Configuration file paths.

All configuration file paths should be defined here as a single source of truth.
This ensures consistency, discoverability, and easier refactoring.
"""

from pathlib import Path

# Tournament configuration
TOURNAMENT_CONFIG_PATH = Path("config/tournament/tournament.json")

# Blind schedule configuration
BLIND_SCHEDULE_CONFIG_PATH = Path("config/blind_schedule/blind_schedule.json")

# Poker game configuration
POKER_CONFIG_PATH = Path("config/poker/poker.json")
