"""Tournament configuration management."""

from src.config.tournament.config import (
    PayoutStructure,
    TournamentConfig,
    calculate_prize_pool,
)
from src.config.tournament.config_loader import TournamentConfigLoader
from src.config.file_paths import TOURNAMENT_CONFIG_PATH

__all__ = [
    "PayoutStructure",
    "TournamentConfig",
    "TournamentConfigLoader",
    "TOURNAMENT_CONFIG_PATH",
    "calculate_prize_pool",
]
