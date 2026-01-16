"""Tournament configuration data structures."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.models.blinds import BlindLevel
from src.domain.models.chips import ChipAmount


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
class BlindScheduleConfig:
    """Tournament blind schedule defining when each blind level applies.

    Blinds advance based on hand number. Each entry specifies:
    - The blind level (small/big blind amounts)
    - Starting hand number (inclusive)
    - Duration in number of hands

    Example:
        Level 1: hands 1-10 (10 hands)
        Level 2: hands 11-20 (10 hands)
        Level 3: hands 21-30 (10 hands)

    Entries are stored sorted by start_hand for efficient lookup.
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
                        f"Blind schedule entries overlap: "
                        f"entry {prev_entry.level.level} ends at hand {prev_end}, "
                        f"but entry {entry.level.level} starts at hand {entry.start_hand}"
                    )
                if entry.start_hand > prev_end:
                    raise ValueError(
                        f"Blind schedule entries have gaps: "
                        f"entry {prev_entry.level.level} ends at hand {prev_end}, "
                        f"but entry {entry.level.level} starts at hand {entry.start_hand}"
                    )

        object.__setattr__(self, "entries", tuple(sorted_entries))

    def get_blind_level_for_hand(self, hand_number: int) -> BlindLevel:
        """Get the blind level that applies to the given hand number.

        Returns the last entry if hand_number exceeds all entries.
        """
        if hand_number < 1:
            raise ValueError(f"Hand number must be at least 1: {hand_number}")

        for entry in reversed(self.entries):
            if entry.applies_to_hand(hand_number):
                return entry.level

        return self.entries[-1].level


@dataclass(frozen=True, slots=True)
class TournamentConfig:
    buy_in_amount: ChipAmount
    starting_chip_stack: ChipAmount
    total_prize_pool: ChipAmount
    payout_structure: str
    blind_schedule: BlindScheduleConfig | None = None

    def __post_init__(self) -> None:
        if self.buy_in_amount.value <= 0:
            raise ValueError(f"Buy-in must be positive: {self.buy_in_amount.value}")
        if self.starting_chip_stack.value <= 0:
            raise ValueError(
                f"Starting chip stack must be positive: {self.starting_chip_stack.value}"
            )
        if self.total_prize_pool.value < 0:
            raise ValueError(f"Total prize pool cannot be negative: {self.total_prize_pool.value}")
