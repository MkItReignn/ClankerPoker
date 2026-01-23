from __future__ import annotations

from dataclasses import dataclass, field, replace
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


@dataclass(frozen=True, slots=True)
class Player:
    id: PlayerId
    name: str
    bot_id: BotId
    seat: Seat
    remaining_chips: ChipAmount
    hole_cards: Hand | None
    betting_status: BettingRoundActionStatus
    participation_status: HandParticipationStatus
    total_invested_this_hand: ChipAmount = field(default_factory=lambda: ChipAmount(0))
    hands_played: int = 0
    elimination_hand_number: int | None = None
    table_finish_position: int | None = None
    can_raise: bool = True  # Can this player raise in current betting round? (WSOP Rule 96)
    stack_at_hand_start: ChipAmount | None = None  # For elimination tiebreaker (SIMUL-004)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Player id cannot be empty")
        if not self.name:
            raise ValueError("Player name cannot be empty")
        if self.remaining_chips.value < 0:
            raise ValueError(f"Remaining chips cannot be negative: {self.remaining_chips.value}")
        if self.total_invested_this_hand.value < 0:
            raise ValueError(
                f"Total invested cannot be negative: {self.total_invested_this_hand.value}"
            )
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
        """Player can take action (needs action, has chips, and is in hand)."""
        return self.needs_action() and self.has_chips() and self.is_in_hand()

    def has_acted_this_round(self) -> bool:
        """Check if player has acted this betting round."""
        return self.betting_status == BettingRoundActionStatus.ACTED

    def is_all_in(self) -> bool:
        """Player has acted and has no chips left."""
        return self.total_invested_this_hand.value > 0 and self.remaining_chips.value == 0

    def has_chips(self) -> bool:
        return self.remaining_chips.value > 0

    def total_stack(self) -> ChipAmount:
        return self.remaining_chips + self.total_invested_this_hand

    def reset_for_new_hand(self, hole_cards: Hand) -> Player:
        """Reset player state for a new hand.

        Sets hole cards, resets betting status to NEEDS_ACTION,
        sets participation status to IN_HAND, resets investment,
        resets can_raise to True, and captures stack_at_hand_start
        for elimination tiebreaker purposes (SIMUL-004).

        Returns a new Player instance (immutable).
        """
        return replace(
            self,
            hole_cards=hole_cards,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
            participation_status=HandParticipationStatus.IN_HAND,
            total_invested_this_hand=ChipAmount(0),
            can_raise=True,
            stack_at_hand_start=self.remaining_chips,
        )

    def reset_for_new_round(self) -> Player:
        """Reset player state for a new betting round.

        Resets betting_status to NEEDS_ACTION and can_raise to True
        for players who are in hand and not all-in.

        Returns a new Player instance (immutable).
        """
        if self.is_in_hand() and not self.is_all_in():
            return replace(
                self,
                betting_status=BettingRoundActionStatus.NEEDS_ACTION,
                can_raise=True,
            )
        return self
