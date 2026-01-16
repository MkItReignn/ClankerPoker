"""Tournament configuration data structures."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.config.blind_schedule.config import BlindSchedule
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
class TournamentConfig:
    buy_in_amount: ChipAmount
    starting_chip_stack: ChipAmount
    payout_structure: PayoutStructure
    blind_schedule: BlindSchedule

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
