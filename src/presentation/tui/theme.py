from __future__ import annotations

from typing import ClassVar


class PlayerTheme:
    SEAT_COLORS: ClassVar[dict[int, str]] = {
        0: "#9b5de5",
        1: "#f15bb5",
        2: "#38b000",
        3: "#00bbf9",
        4: "#00f5d4",
        5: "#ccff33",
    }
    DEFAULT_COLOR: ClassVar[str] = "#ffffff"

    @classmethod
    def get_color(cls, seat: int) -> str:
        return cls.SEAT_COLORS.get(seat, cls.DEFAULT_COLOR)

    @classmethod
    def format_name(cls, name: str, seat: int, bold: bool = True) -> str:
        color = cls.get_color(seat)
        if bold:
            return f"[{color} bold]{name}[/{color} bold]"
        return f"[{color}]{name}[/{color}]"

    @classmethod
    def format_name_italic(cls, name: str, seat: int) -> str:
        color = cls.get_color(seat)
        return f"[{color} italic]{name}:[/{color} italic]"
