"""Protocols for game history persistence."""

from __future__ import annotations

from typing import Protocol, TypeVar

THistory = TypeVar("THistory")


class GameHistoryRepository(Protocol[THistory]):
    """Protocol for persisting and loading game history.

    Implementations handle the actual storage mechanism (JSON files, database, etc.).

    Type Parameters:
        THistory: The history type to persist.
    """

    def save(self, history: THistory) -> None:
        """Save game history to persistent storage.

        Args:
            history: The history object to save.

        Raises:
            IOError: If saving fails.
        """
        ...

    def load(self, game_id: str) -> THistory | None:
        """Load game history from persistent storage.

        Args:
            game_id: The unique identifier of the game.

        Returns:
            The loaded history, or None if not found.

        Raises:
            IOError: If loading fails (other than not found).
        """
        ...

    def exists(self, game_id: str) -> bool:
        """Check if history exists for a game.

        Args:
            game_id: The unique identifier of the game.

        Returns:
            True if history exists, False otherwise.
        """
        ...

    def delete(self, game_id: str) -> bool:
        """Delete game history from persistent storage.

        Args:
            game_id: The unique identifier of the game.

        Returns:
            True if deleted, False if not found.

        Raises:
            IOError: If deletion fails.
        """
        ...
