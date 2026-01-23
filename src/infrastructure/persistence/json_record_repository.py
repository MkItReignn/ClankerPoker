from __future__ import annotations

from pathlib import Path

import orjson

from src.application.poker.records.models import GameRecord
from src.logger.factories import get_generic_logger


class JsonGameRecordRepository:
    def __init__(self, base_path: str | Path = "data") -> None:
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)
        self._logger = get_generic_logger(__name__.removeprefix("src."))
        self._game_id_to_file: dict[str, Path] = {}
        self._build_index()

    def _build_index(self) -> None:
        for file_path in self._base_path.glob("record_*.jsonl"):
            try:
                json_bytes = file_path.read_bytes().strip()
                data = orjson.loads(json_bytes)
                game_id = data.get("game_id")
                if game_id:
                    self._game_id_to_file[game_id] = file_path
            except orjson.JSONDecodeError:
                self._logger.warning(f"Failed to parse {file_path}")

    def _generate_filename(self, record: GameRecord) -> str:
        timestamp = record.created_at.strftime("%Y-%m-%dT%H-%M-%S")
        return f"record_{timestamp}.jsonl"

    def save(self, record: GameRecord) -> None:
        if record.game_id in self._game_id_to_file:
            file_path = self._game_id_to_file[record.game_id]
        else:
            file_path = self._base_path / self._generate_filename(record)
            self._game_id_to_file[record.game_id] = file_path

        data = record.to_dict()
        json_bytes = orjson.dumps(data)
        file_path.write_bytes(json_bytes + b"\n")

        self._logger.debug(f"Saved game record to {file_path}")

    def load(self, game_id: str) -> GameRecord | None:
        file_path = self._game_id_to_file.get(game_id)
        if file_path is None or not file_path.exists():
            return None

        try:
            json_bytes = file_path.read_bytes().strip()
            data = orjson.loads(json_bytes)
            return GameRecord.from_dict(data)
        except orjson.JSONDecodeError:
            self._logger.error(f"Failed to parse JSON from {file_path}")
            return None

    def exists(self, game_id: str) -> bool:
        file_path = self._game_id_to_file.get(game_id)
        return file_path is not None and file_path.exists()

    def delete(self, game_id: str) -> bool:
        file_path = self._game_id_to_file.get(game_id)
        if file_path is None or not file_path.exists():
            return False

        file_path.unlink()
        del self._game_id_to_file[game_id]
        self._logger.debug(f"Deleted game record at {file_path}")
        return True

    def list_games(self) -> list[str]:
        return list(self._game_id_to_file.keys())
