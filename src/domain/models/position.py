from dataclasses import dataclass
from enum import Enum

from src.domain.models.seat import Seat


class PositionName(Enum):
    """Position names relative to button.

    Note: In heads-up, Button and Small Blind are the same person.
    In normal play (3+ players), these are distinct positions.
    """

    BUTTON = "button"
    SMALL_BLIND = "small_blind"
    BIG_BLIND = "big_blind"
    UNDER_THE_GUN = "utg"
    UTG_PLUS_ONE = "utg_plus_one"
    CUTOFF = "cutoff"

    def to_short_string(self) -> str:
        """Convert position name to short string representation (BTN, SB, BB, UTG, UTG+1, CO)."""
        return {
            PositionName.BUTTON: "BTN",
            PositionName.SMALL_BLIND: "SB",
            PositionName.BIG_BLIND: "BB",
            PositionName.UNDER_THE_GUN: "UTG",
            PositionName.UTG_PLUS_ONE: "UTG+1",
            PositionName.CUTOFF: "CO",
        }[self]


@dataclass(frozen=True, slots=True)
class TablePositionMapping:
    """Maps position names to seat indices for current hand.

    This represents the position structure for a specific hand.
    All positions are calculated upfront, skipping eliminated players.
    In heads-up, button_seat == small_blind_seat.

    Position mapping by active player count:
    - 2 players (heads-up): BTN/SB, BB
    - 3 players: BTN, SB, BB (no UTG/UTG+1/Cutoff)
    - 4 players: BTN, SB, BB, UTG
    - 5 players: BTN, SB, BB, UTG, CO
    - 6 players: BTN, SB, BB, UTG, UTG+1, CO
    """

    button_seat: Seat
    small_blind_seat: Seat
    big_blind_seat: Seat
    utg_seat: Seat | None
    utg_plus_one_seat: Seat | None
    cutoff_seat: Seat | None
    is_heads_up: bool
    active_players_count: int
    total_seats_at_table: int

    def __post_init__(self) -> None:
        if self.button_seat < 0:
            raise ValueError(
                f"Button seat must be non-negative: {self.button_seat}"
            )
        if self.small_blind_seat < 0:
            raise ValueError(
                f"Small blind seat must be non-negative: {self.small_blind_seat}"
            )
        if self.big_blind_seat < 0:
            raise ValueError(
                f"Big blind seat must be non-negative: {self.big_blind_seat}"
            )
        if self.active_players_count < 2:
            raise ValueError(
                f"Active players count must be at least 2: {self.active_players_count}"
            )
        if self.total_seats_at_table < 2:
            raise ValueError(
                f"Total seats at table must be at least 2: {self.total_seats_at_table}"
            )
        if self.is_heads_up and self.button_seat != self.small_blind_seat:
            raise ValueError(
                "In heads-up, button_seat must equal small_blind_seat"
            )
        if self.is_heads_up and self.active_players_count != 2:
            raise ValueError(
                f"Heads-up requires 2 active players, got {self.active_players_count}"
            )

    def get_seat_for_position(
        self, position_name: PositionName
    ) -> Seat | None:
        """Get seat for a given position name.

        Returns None if position doesn't exist for current player count.

        Note: BUTTON, SMALL_BLIND, and BIG_BLIND always return a Seat.
        UTG, UTG+1, and CUTOFF may return None depending on player count.
        """
        if position_name == PositionName.BUTTON:
            return self.button_seat
        elif position_name == PositionName.SMALL_BLIND:
            return self.small_blind_seat
        elif position_name == PositionName.BIG_BLIND:
            return self.big_blind_seat
        elif position_name == PositionName.UNDER_THE_GUN:
            return self.utg_seat
        elif position_name == PositionName.UTG_PLUS_ONE:
            return self.utg_plus_one_seat
        elif position_name == PositionName.CUTOFF:
            return self.cutoff_seat

    def get_position_for_seat(self, seat: Seat) -> PositionName | None:
        if self.button_seat == seat:
            return PositionName.BUTTON
        if self.small_blind_seat == seat:
            return PositionName.SMALL_BLIND
        if self.big_blind_seat == seat:
            return PositionName.BIG_BLIND
        if self.utg_seat == seat:
            return PositionName.UNDER_THE_GUN
        if self.utg_plus_one_seat == seat:
            return PositionName.UTG_PLUS_ONE
        if self.cutoff_seat == seat:
            return PositionName.CUTOFF

        return None
