"""JSON file-based game history repository."""

from __future__ import annotations

from pathlib import Path

import orjson

from src.application.poker.history.models import GameHistory
from src.logger.factories import get_generic_logger


class JsonGameHistoryRepository:
    """JSON file-based repository for game history.

    Persists GameHistory objects to JSON files in a specified directory.
    The repository orchestrates file I/O while models handle their own serialization.
    """

    def __init__(self, base_path: str | Path = "data") -> None:
        """Initialize the repository.

        Args:
            base_path: Base directory for storing game files.
        """
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)
        self._logger = get_generic_logger(__name__.removeprefix("src."))

    def _get_file_path(self, game_id: str) -> Path:
        safe_id = "".join(c for c in game_id if c.isalnum() or c in "-_")
        return self._base_path / f"history_{safe_id}.jsonl"

    def save(self, history: GameHistory) -> None:
        file_path = self._get_file_path(history.game_id)

        # Model knows how to serialize itself
        data = history.to_dict()

        # orjson handles datetime serialization automatically
        json_bytes = orjson.dumps(data)

        file_path.write_bytes(json_bytes + b"\n")

        self._logger.debug(f"Saved game history to {file_path}")

    def load(self, game_id: str) -> GameHistory | None:
        file_path = self._get_file_path(game_id)

        if not file_path.exists():
            return None

        json_bytes = file_path.read_bytes().strip()
        data = orjson.loads(json_bytes)

        return GameHistory.from_dict(data)

    def exists(self, game_id: str) -> bool:
        return self._get_file_path(game_id).exists()

    def delete(self, game_id: str) -> bool:
        file_path = self._get_file_path(game_id)

        if not file_path.exists():
            return False

        file_path.unlink()
        self._logger.debug(f"Deleted game history at {file_path}")
        return True

    def list_games(self) -> list[str]:
        return [p.stem for p in self._base_path.glob("*.jsonl")]
