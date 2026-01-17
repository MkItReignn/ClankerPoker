from __future__ import annotations

from dataclasses import dataclass

from src.domain.models.blinds import BlindLevel
from src.domain.models.card import Card
from src.domain.models.chips import ChipAmount
from src.domain.models.game import GamePhase
from src.domain.models.hand import Hand
from src.domain.models.player import PlayerId
from src.domain.models.position import PositionName
from src.domain.models.seat import Seat


@dataclass(frozen=True, slots=True)
class ActingPlayerState:
    player_id: PlayerId
    player_name: str
    hole_cards: Hand
    position: PositionName | None
    stack: ChipAmount


@dataclass(frozen=True, slots=True)
class HandState:
    phase: GamePhase
    community_cards: tuple[Card, ...]
    pot_total: ChipAmount
    hand_number: int
    current_bet: ChipAmount
    blinds: BlindLevel


@dataclass(frozen=True, slots=True)
class OpponentCurrentState:
    player_id: str
    name: str
    seat: Seat
    position: PositionName | None
    stack: ChipAmount
    is_folded: bool
    is_all_in: bool
    invested_this_hand: ChipAmount


@dataclass(frozen=True, slots=True)
class CurrentHandHistory:
    text: str


@dataclass(frozen=True, slots=True)
class PreviousHandsHistory:
    text: str


@dataclass(frozen=True, slots=True)
class PokerDecisionContext:
    acting_player: ActingPlayerState
    hand_state: HandState
    opponents: tuple[OpponentCurrentState, ...]
    current_hand_history: CurrentHandHistory
    previous_hand_history: PreviousHandsHistory

    @property
    def stack_in_bb(self) -> float:
        if self.hand_state.blinds.big_blind.value == 0:
            return 0.0
        return self.acting_player.stack.value / self.hand_state.blinds.big_blind.value

    @property
    def pot_odds(self) -> float | None:
        if self.hand_state.current_bet.value == 0:
            return None
        return self.hand_state.pot_total.value / self.hand_state.current_bet.value

    @property
    def is_heads_up(self) -> bool:
        active_opponents = sum(1 for o in self.opponents if not o.is_folded and not o.is_all_in)
        return active_opponents <= 1
