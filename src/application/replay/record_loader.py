from pathlib import Path
from typing import Any

import orjson

from src.application.poker.records.models import GameRecord


class RecordLoadError(Exception):
    pass


class RecordLoader:
    @staticmethod
    def load(path: Path) -> GameRecord:
        if not path.exists():
            raise RecordLoadError(f"Record file not found: {path}")

        if not path.is_file():
            raise RecordLoadError(f"Path is not a file: {path}")

        try:
            json_bytes: bytes = path.read_bytes()
            data: dict[str, Any] = orjson.loads(json_bytes)
            return GameRecord.from_dict(data)
        except orjson.JSONDecodeError as e:
            raise RecordLoadError(
                f"Invalid JSON in record file {path}: {e}"
            ) from e
        except KeyError as e:
            raise RecordLoadError(
                f"Missing required field in record {path}: {e}"
            ) from e
        except ValueError as e:
            raise RecordLoadError(f"Invalid data in record {path}: {e}") from e
