from __future__ import annotations

from typing import Any

from src.domain.models.card import Rank


class HandDescriptionFormatter:
    @classmethod
    def format(cls, hand_eval: dict[str, Any]) -> str:
        rank = hand_eval.get("rank", 1)
        kickers = hand_eval.get("kickers", [])

        if rank == 10:
            return "Royal Flush"

        if rank == 9:
            high = cls._kicker_short(kickers, 0)
            return f"Straight Flush, {high}-high"

        if rank == 8:
            quads = cls._kicker_plural(kickers, 0)
            return f"Four {quads}"

        if rank == 7:
            trips = cls._kicker_plural(kickers, 0)
            pair = cls._kicker_plural(kickers, 1)
            return f"Full House, {trips} over {pair}"

        if rank == 6:
            high = cls._kicker_short(kickers, 0)
            return f"Flush, {high}-high"

        if rank == 5:
            high = cls._kicker_short(kickers, 0)
            return f"Straight, {high}-high"

        if rank == 4:
            trips = cls._kicker_plural(kickers, 0)
            return f"Three {trips}"

        if rank == 3:
            high_pair = cls._kicker_plural(kickers, 0)
            low_pair = cls._kicker_plural(kickers, 1)
            return f"Two Pair, {high_pair} and {low_pair}"

        if rank == 2:
            pair = cls._kicker_plural(kickers, 0)
            return f"Pair of {pair}"

        high = cls._kicker_short(kickers, 0)
        return f"High Card, {high}"

    @staticmethod
    def _kicker_plural(kickers: list[int], index: int) -> str:
        if index >= len(kickers):
            return "?"
        return Rank(kickers[index]).to_plural_string()

    @staticmethod
    def _kicker_short(kickers: list[int], index: int) -> str:
        if index >= len(kickers):
            return "?"
        return Rank(kickers[index]).to_short_string()
