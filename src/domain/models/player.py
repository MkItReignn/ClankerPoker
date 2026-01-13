from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.domain.models.bot import BotId
from src.domain.models.chips import ChipAmount
from src.domain.models.hand import Hand
from src.domain.models.seat import Seat

PlayerId = str


class PlayerStatus(Enum):
    ACTIVE = "active"
    FOLDED = "folded"
    ALL_IN = "all_in"
    ELIMINATED = "eliminated"


@dataclass(slots=True)
class Player:
    id: PlayerId
    bot_id: BotId
    seat: Seat
    chips: ChipAmount
    hole_cards: Hand | None
    status: PlayerStatus
    current_bet: ChipAmount
    has_acted_this_round: bool
    hands_played: int = 0
    elimination_hand_number: int | None = None
    table_finish_position: int | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Player id cannot be empty")
        if self.chips.value < 0:
            raise ValueError(f"Chips cannot be negative: {self.chips.value}")
        if self.current_bet.value < 0:
            raise ValueError(f"Current bet cannot be negative: {self.current_bet.value}")
        if self.hands_played < 0:
            raise ValueError(f"Hands played cannot be negative: {self.hands_played}")
        if self.elimination_hand_number is not None and self.elimination_hand_number < 1:
            raise ValueError(
                f"Elimination hand number must be at least 1: {self.elimination_hand_number}"
            )
        if self.table_finish_position is not None and self.table_finish_position < 1:
            raise ValueError(
                f"Table finish position must be at least 1: {self.table_finish_position}"
            )

    def is_active(self) -> bool:
        return self.status == PlayerStatus.ACTIVE

    def is_in_hand(self) -> bool:
        return self.status in (PlayerStatus.ACTIVE, PlayerStatus.ALL_IN)

    def can_act(self) -> bool:
        return self.is_active() and not self.has_acted_this_round

    def has_chips(self) -> bool:
        return self.chips.value > 0

    def total_stack(self) -> ChipAmount:
        return self.chips + self.current_bet
