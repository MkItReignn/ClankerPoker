"""Shared JSON file loading with caching and error handling."""

import json
from pathlib import Path
from typing import Protocol, final

import structlog


class FileReader(Protocol):
    """Protocol for file reading (enables dependency injection for testing)."""

    def read_text(self, path: Path, encoding: str = "utf-8") -> str:
        """Read text from file.

        Args:
            path: Path to file to read.
            encoding: Text encoding to use.

        Returns:
            File contents as string.

        Raises:
            OSError: If file cannot be read.
        """
        ...

    def exists(self, path: Path) -> bool:
        """Check if file exists.

        Args:
            path: Path to check.

        Returns:
            True if file exists, False otherwise.
        """
        ...


@final
class DefaultFileReader:
    """Default file reader implementation using Path methods."""

    def read_text(self, path: Path, encoding: str = "utf-8") -> str:
        return path.read_text(encoding=encoding)

    def exists(self, path: Path) -> bool:
        return path.exists()


@final
class JsonFileLoader:
    """Loads JSON files with caching and error handling."""

    def __init__(
        self,
        config_path: Path,
        logger: structlog.BoundLogger,
        *,
        file_reader: FileReader | None = None,
    ) -> None:
        """Initialize JSON file loader.

        Args:
            config_path: Path to JSON configuration file.
            logger: Logger for error and info messages.
            file_reader: Optional file reader implementation (for testing).
                Defaults to DefaultFileReader.
        """
        self._config_path = config_path
        self._logger = logger
        self._file_reader = file_reader or DefaultFileReader()
        self._cached: dict[str, object] | None = None

    def load(self) -> dict[str, object]:
        """Load entire JSON file.

        Returns:
            Parsed JSON as dictionary.

        Raises:
            FileNotFoundError: If config file does not exist.
            ValueError: If JSON is invalid or root is not an object.
            RuntimeError: If file cannot be read.
        """
        if self._cached is not None:
            return self._cached

        if not self._file_reader.exists(self._config_path):
            self._logger.error(
                "config_file_not_found",
                config_path=str(self._config_path),
            )
            raise FileNotFoundError(
                f"Configuration file not found: {self._config_path}"
            )

        try:
            raw_text = self._file_reader.read_text(
                self._config_path, encoding="utf-8"
            )
            loaded_config = json.loads(raw_text)
        except json.JSONDecodeError as e:
            self._logger.error(
                "config_invalid_json",
                config_path=str(self._config_path),
                error=str(e),
            )
            raise ValueError(f"Invalid JSON in config file: {e}") from e
        except Exception as e:
            self._logger.error(
                "config_load_failed",
                config_path=str(self._config_path),
                error=str(e),
            )
            raise RuntimeError(f"Failed to load config: {e}") from e

        if not isinstance(loaded_config, dict):
            raise ValueError("Config file must contain a JSON object")

        self._cached = loaded_config
        self._logger.info(
            "config_loaded",
            config_path=str(self._config_path),
        )
        return self._cached
