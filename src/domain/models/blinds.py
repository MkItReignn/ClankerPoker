from __future__ import annotations

from dataclasses import dataclass

from src.domain.models.chips import ChipAmount


@dataclass(frozen=True, slots=True)
class BlindLevel:
    small_blind: ChipAmount
    big_blind: ChipAmount
    level: int

    def __post_init__(self) -> None:
        if self.level < 1:
            raise ValueError(f"Blind level must be at least 1: {self.level}")
        if self.big_blind.value < self.small_blind.value:
            raise ValueError(
                f"Big blind must be >= small blind: {self.big_blind.value} < {self.small_blind.value}"
            )
        if self.big_blind.value != self.small_blind.value * 2:
            raise ValueError(
                f"Big blind must be exactly 2x small blind: {self.big_blind.value} != {self.small_blind.value * 2}"
            )


@dataclass(frozen=True, slots=True)
class BlindScheduleEntry:
    """Defines a blind level and when it applies."""

    level: BlindLevel
    start_hand: int
    duration_hands: int

    def __post_init__(self) -> None:
        if self.start_hand < 1:
            raise ValueError(f"Start hand must be at least 1: {self.start_hand}")
        if self.duration_hands < 1:
            raise ValueError(f"Duration must be at least 1 hand: {self.duration_hands}")

    def applies_to_hand(self, hand_number: int) -> bool:
        """Check if this schedule entry applies to the given hand number."""
        end_hand = self.start_hand + self.duration_hands
        return self.start_hand <= hand_number < end_hand


@dataclass(frozen=True, slots=True)
class BlindSchedule:
    """Tournament blind schedule defining when each blind level applies.

    Blinds advance based on hand number. Each entry specifies:
    - The blind level (small/big blind amounts)
    - Starting hand number (inclusive)
    - Duration in number of hands

    Example:
        Level 1: hands 1-10 (10 hands)
        Level 2: hands 11-20 (10 hands)
        Level 3: hands 21-30 (10 hands)
    """

    entries: tuple[BlindScheduleEntry, ...]

    def __post_init__(self) -> None:
        if not self.entries:
            raise ValueError("Blind schedule must have at least one entry")

        sorted_entries = sorted(self.entries, key=lambda e: e.start_hand)
        for i, entry in enumerate(sorted_entries):
            if i > 0:
                prev_entry = sorted_entries[i - 1]
                prev_end = prev_entry.start_hand + prev_entry.duration_hands
                if entry.start_hand < prev_end:
                    raise ValueError(
                        "Blind schedule entries overlap: "
                        + f"entry {prev_entry.level.level} ends at hand {prev_end}, "
                        + f"but entry {entry.level.level} starts at hand {entry.start_hand}"
                    )

    def get_blind_level_for_hand(self, hand_number: int) -> BlindLevel:
        """Get the blind level that applies to the given hand number.

        Returns the last entry if hand_number exceeds all entries.
        """
        if hand_number < 1:
            raise ValueError(f"Hand number must be at least 1: {hand_number}")

        for entry in sorted(self.entries, key=lambda e: e.start_hand, reverse=True):
            if entry.applies_to_hand(hand_number):
                return entry.level

        return sorted(self.entries, key=lambda e: e.start_hand, reverse=True)[0].level
