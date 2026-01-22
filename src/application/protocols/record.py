"""Protocols for game record persistence."""

from __future__ import annotations

from typing import Protocol, TypeVar

TRecord = TypeVar("TRecord")


class GameRecordRepository(Protocol[TRecord]):
    """Protocol for persisting and loading game records.

    Implementations handle the actual storage mechanism (JSON files, database, etc.).

    Type Parameters:
        TRecord: The record type to persist.
    """

    def save(self, record: TRecord) -> None:
        """Save game record to persistent storage.

        Args:
            record: The record object to save.

        Raises:
            IOError: If saving fails.
        """
        ...

    def load(self, game_id: str) -> TRecord | None:
        """Load game record from persistent storage.

        Args:
            game_id: The unique identifier of the game.

        Returns:
            The loaded record, or None if not found.

        Raises:
            IOError: If loading fails (other than not found).
        """
        ...

    def exists(self, game_id: str) -> bool:
        """Check if record exists for a game.

        Args:
            game_id: The unique identifier of the game.

        Returns:
            True if record exists, False otherwise.
        """
        ...

    def delete(self, game_id: str) -> bool:
        """Delete game record from persistent storage.

        Args:
            game_id: The unique identifier of the game.

        Returns:
            True if deleted, False if not found.

        Raises:
            IOError: If deletion fails.
        """
        ...
