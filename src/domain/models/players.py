"""Immutable Players collection for managing player state."""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any, Self

from src.domain.models.player import HandParticipationStatus, Player, PlayerId
from src.domain.models.seat import Seat


@dataclass(frozen=True, slots=True)
class Players:
    """Immutable collection of players keyed by player_id.

    Provides O(1) lookup by player_id (most common operation).
    Python 3.7+ dicts maintain insertion order (preserves seat ordering).

    All update operations return new Players instances.
    """

    _players: dict[str, Player]

    def __post_init__(self) -> None:
        if len(self._players) < 2:
            raise ValueError(
                f"Players collection must have at least 2 players: {len(self._players)}"
            )
        if len(self._players) > 6:
            raise ValueError(
                f"Players collection cannot have more than 6 players: {len(self._players)}"
            )

        seats = [p.seat.value for p in self._players.values()]
        if len(seats) != len(set(seats)):
            raise ValueError("Player seats must be unique")

    def __len__(self) -> int:
        return len(self._players)

    def __iter__(self) -> Iterator[Player]:
        return iter(self._players.values())

    def __getitem__(self, index: int) -> Player:
        """Get player by position index. Maintains insertion order."""
        return list(self._players.values())[index]

    @classmethod
    def from_list(cls, players: list[Player]) -> Self:
        """Create Players collection from a list of players."""
        return cls(_players={p.id: p for p in players})

    def to_list(self) -> list[Player]:
        """Convert to list for compatibility. Returns a new list each time."""
        return list(self._players.values())

    def get_by_id(self, player_id: PlayerId) -> Player | None:
        """Get player by ID. O(1) lookup."""
        return self._players.get(player_id)

    def get_by_seat(self, seat: Seat) -> Player | None:
        """Get player by seat. O(n) but less common operation."""
        for player in self._players.values():
            if player.seat == seat:
                return player
        return None

    def active(self) -> tuple[Player, ...]:
        """Get all active (non-eliminated) players."""
        return tuple(
            p
            for p in self._players.values()
            if p.participation_status != HandParticipationStatus.ELIMINATED
        )

    def active_ids(self) -> frozenset[PlayerId]:
        """Get IDs of all active (non-eliminated) players."""
        return frozenset(
            p.id
            for p in self._players.values()
            if p.participation_status != HandParticipationStatus.ELIMINATED
        )

    def in_hand(
        self, excluded_player_id: PlayerId | None = None
    ) -> tuple[Player, ...]:
        """Get all players currently in hand, optionally excluding a specific player."""
        players = [p for p in self._players.values() if p.is_in_hand()]
        if excluded_player_id is not None:
            players = [p for p in players if p.id != excluded_player_id]
        return tuple(players)

    def players_in_hand_and_not_all_in(self) -> tuple[Player, ...]:
        """Get all players who are in the hand and not all-in (can still act)."""
        return tuple(
            p
            for p in self._players.values()
            if p.is_in_hand() and not p.is_all_in()
        )

    def are_all_players_all_in(self) -> bool:
        """Check if all players in hand are all-in (no more betting possible)."""
        players_in_hand = self.in_hand()

        if len(players_in_hand) <= 1:
            return False

        # All players are all-in if no one can act
        players_in_hand_and_not_all_in = self.players_in_hand_and_not_all_in()
        return len(players_in_hand_and_not_all_in) == 0

    def get_all_players_invested_in_current_hand(self) -> list[Player]:
        """Get all players who have invested chips in the current hand (including folded)."""
        return [
            p
            for p in self._players.values()
            if p.total_invested_this_hand.value > 0
        ]

    def replace_player(
        self, player_id: PlayerId, updated_player: Player
    ) -> Self:
        """Replace a single player. Returns new Players instance.

        Raises ValueError if player_id not found.
        """
        if player_id not in self._players:
            raise ValueError(f"Player {player_id} not found in collection")

        return Players(_players={**self._players, player_id: updated_player})

    def replace_at_index(self, index: int, updated_player: Player) -> Self:
        """Replace player at index. Returns new Players instance."""
        if index < 0 or index >= len(self._players):
            raise IndexError(
                f"Index {index} out of range for {len(self._players)} players"
            )

        keys = list(self._players.keys())
        player_id = keys[index]
        return Players(_players={**self._players, player_id: updated_player})

    def replace_all(self, updates: dict[PlayerId, Player]) -> Self:
        """Replace multiple players at once. Returns new Players instance."""
        return Players(_players={**self._players, **updates})

    def transform_all(self, transform: Callable[[Player], Player]) -> Self:
        """Apply transformation to all players. Returns new Players instance."""
        return Players(
            _players={pid: transform(p) for pid, p in self._players.items()}
        )

    def transform_filtered(
        self,
        predicate: Callable[[Player], bool],
        transform: Callable[[Player], Player],
    ) -> Self:
        """Apply transformation to players matching predicate. Returns new Players instance."""
        return Players(
            _players={
                pid: transform(p) if predicate(p) else p
                for pid, p in self._players.items()
            }
        )

    def to_dict(self) -> list[dict[str, Any]]:
        return [player.to_dict() for player in self._players.values()]
