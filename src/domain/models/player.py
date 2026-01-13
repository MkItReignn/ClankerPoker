from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from src.domain.models.bot import BotId
from src.domain.models.chips import ChipAmount
from src.domain.models.hand import Hand
from src.domain.models.seat import Seat

PlayerId = str


class BettingRoundActionStatus(Enum):
    """Whether the player has acted in the current betting round."""

    NEEDS_ACTION = "needs_action"
    ACTED = "acted"


class HandParticipationStatus(Enum):
    """Whether the player is still participating in the current hand."""

    IN_HAND = "in_hand"
    FOLDED = "folded"
    ELIMINATED = "eliminated"


@dataclass(slots=True)
class Player:
    id: PlayerId
    bot_id: BotId
    seat: Seat
    chips: ChipAmount
    hole_cards: Hand | None
    betting_status: BettingRoundActionStatus
    participation_status: HandParticipationStatus
    current_bet: ChipAmount
    total_invested_this_hand: ChipAmount = field(default_factory=lambda: ChipAmount(0))
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

    def needs_action(self) -> bool:
        """Player needs to take action this round."""
        return self.betting_status == BettingRoundActionStatus.NEEDS_ACTION

    def is_in_hand(self) -> bool:
        """Player is still in the hand (not folded, not eliminated)."""
        return self.participation_status == HandParticipationStatus.IN_HAND

    def can_act(self) -> bool:
        """Player can take action (needs action and has chips)."""
        return self.needs_action() and self.has_chips()

    def has_acted_this_round(self) -> bool:
        """Check if player has acted this betting round."""
        return self.betting_status == BettingRoundActionStatus.ACTED

    def is_all_in(self) -> bool:
        """Player has acted and has no chips left."""
        return self.betting_status == BettingRoundActionStatus.ACTED and self.chips.value == 0

    def has_chips(self) -> bool:
        return self.chips.value > 0

    def total_stack(self) -> ChipAmount:
        return self.chips + self.current_bet
