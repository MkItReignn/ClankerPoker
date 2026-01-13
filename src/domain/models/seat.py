from __future__ import annotations

from enum import IntEnum


class Seat(IntEnum):
    SEAT_0 = 0
    SEAT_1 = 1
    SEAT_2 = 2
    SEAT_3 = 3
    SEAT_4 = 4
    SEAT_5 = 5

    @classmethod
    def from_int(cls, value: int) -> Seat:
        if not (0 <= value <= 5):
            raise ValueError(f"Seat must be between 0 and 5, got {value}")
        return cls(value)
