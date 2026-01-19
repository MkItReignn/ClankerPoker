"""JSON file-based game history repository."""

from __future__ import annotations

import logging
from pathlib import Path

import orjson

from src.application.poker.history.models import GameHistory

logger = logging.getLogger(__name__)


class JsonGameHistoryRepository:
    """JSON file-based repository for game history.

    Persists GameHistory objects to JSON files in a specified directory.
    The repository orchestrates file I/O while models handle their own serialization.
    """

    def __init__(self, base_path: str | Path = "data/games") -> None:
        """Initialize the repository.

        Args:
            base_path: Base directory for storing game files.
        """
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, game_id: str) -> Path:
        """Get the file path for a game."""
        # Sanitize game_id for filesystem
        safe_id = "".join(c for c in game_id if c.isalnum() or c in "-_")
        return self._base_path / f"{safe_id}.json"

    def save(self, history: GameHistory) -> None:
        """Save game history to JSON file.

        Args:
            history: The history to save.
        """
        file_path = self._get_file_path(history.game_id)

        # Model knows how to serialize itself
        data = history.to_dict()

        # orjson handles datetime serialization automatically
        json_bytes = orjson.dumps(data, option=orjson.OPT_INDENT_2)

        file_path.write_bytes(json_bytes)

        logger.debug(f"Saved game history to {file_path}")

    def load(self, game_id: str) -> GameHistory | None:
        """Load game history from JSON file.

        Args:
            game_id: The game ID to load.

        Returns:
            The loaded history, or None if not found.
        """
        file_path = self._get_file_path(game_id)

        if not file_path.exists():
            return None

        json_bytes = file_path.read_bytes()
        data = orjson.loads(json_bytes)

        # Model knows how to deserialize itself
        return GameHistory.from_dict(data)

    def exists(self, game_id: str) -> bool:
        """Check if history exists for a game."""
        return self._get_file_path(game_id).exists()

    def delete(self, game_id: str) -> bool:
        """Delete game history.

        Args:
            game_id: The game ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        file_path = self._get_file_path(game_id)

        if not file_path.exists():
            return False

        file_path.unlink()
        logger.debug(f"Deleted game history at {file_path}")
        return True

    def list_games(self) -> list[str]:
        """List all stored game IDs.

        Returns:
            List of game IDs.
        """
        return [p.stem for p in self._base_path.glob("*.json")]
