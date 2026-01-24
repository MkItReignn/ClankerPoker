"""Configuration file paths.

All configuration file paths should be defined here as a single source of truth.
This ensures consistency, discoverability, and easier refactoring.
"""

from pathlib import Path

# Application-wide configuration
ENVIRONMENT_CONFIG_PATH = Path("config/environment.json")

# Tournament configuration
TOURNAMENT_CONFIG_PATH = Path("config/tournament/tournament.json")

# Blind schedule configuration
BLIND_SCHEDULE_CONFIG_PATH = Path("config/blind_schedule/blind_schedule.json")

# Poker game configuration
POKER_CONFIG_PATH = Path("config/poker/poker.yaml")
POKER_PROMPTS_CONFIG_PATH = Path("config/poker/prompts.yaml")
BOT_PLAYERS_CONFIG_PATH = Path("config/poker/bot_players.json")
ACTION_PROVIDER_CONFIG_PATH = Path("config/poker/action_provider.json")

# LLM client configuration
LLM_CONFIG_PATH = Path("config/llm/openrouter.json")
