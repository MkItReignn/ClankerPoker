from __future__ import annotations

from typing import ClassVar


class PlayerRegistry:
    _players: ClassVar[dict[str, int]] = {}

    @classmethod
    def register(cls, player_id: str, seat: int) -> None:
        cls._players[player_id] = seat

    @classmethod
    def get_seat(cls, player_id: str) -> int | None:
        return cls._players.get(player_id)

    @classmethod
    def clear(cls) -> None:
        cls._players.clear()

    @classmethod
    def register_all(cls, players: list[dict]) -> None:
        for player in players:
            player_id = player.get("id", "")
            seat = player.get("seat", 0)
            if player_id:
                cls.register(player_id, seat)
