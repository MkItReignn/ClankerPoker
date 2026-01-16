"""Tournament configuration data structures."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.domain.models.blinds import BlindLevel
from src.domain.models.chips import ChipAmount


class PayoutStructure(str, Enum):
    """Tournament payout structure modes.

    Defines how prize pool is distributed among finishing positions.
    Currently only WINNER_TAKES_ALL is implemented.

    Future payout structures could include:
    - TOP_TWO_SPLIT: e.g., 70/30 split between 1st and 2nd place
    - TOP_THREE_SPLIT: e.g., 50/30/20 split between 1st, 2nd, and 3rd place
    - CUSTOM_PERCENTAGES: Configurable percentage distribution
    """

    WINNER_TAKES_ALL = "WINNER_TAKES_ALL"


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
    payout_structure: PayoutStructure
    blind_schedule: BlindScheduleConfig | None = None

    def __post_init__(self) -> None:
        if self.buy_in_amount.value <= 0:
            raise ValueError(f"Buy-in must be positive: {self.buy_in_amount.value}")
        if self.starting_chip_stack.value <= 0:
            raise ValueError(
                f"Starting chip stack must be positive: {self.starting_chip_stack.value}"
            )


def calculate_prize_pool(buy_in_amount: ChipAmount, number_of_players: int) -> ChipAmount:
    """Calculate tournament prize pool from buy-in and player count.

    Prize pool is the sum of all buy-ins (platform fee handled separately).

    Args:
        buy_in_amount: The buy-in amount per player.
        number_of_players: The number of players who entered the tournament.

    Returns:
        Total prize pool amount.

    Raises:
        ValueError: If number_of_players is less than 1.
    """
    if number_of_players < 1:
        raise ValueError(f"Number of players must be at least 1: {number_of_players}")
    return ChipAmount(buy_in_amount.value * number_of_players)
