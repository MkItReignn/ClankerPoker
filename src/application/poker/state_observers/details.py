from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from src.domain.models.actions import ActionType
from src.domain.models.card import Card
from src.domain.models.chips import ChipAmount
from src.domain.models.game import GamePhase
from src.domain.models.hand import Hand
from src.domain.models.narration import Narration
from src.domain.models.seat import Seat
from src.domain.rules.hand_evaluator import HandEvaluation


# =============================================================================
# Game Lifecycle
# =============================================================================


@dataclass(frozen=True, slots=True)
class GameStartedDetails:
    player_count: int
    starting_chips: ChipAmount

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_count": self.player_count,
            "starting_chips": self.starting_chips.value,
        }


@dataclass(frozen=True, slots=True)
class GameCompletedDetails:
    winner_id: str
    winner_name: str
    total_hands: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "winner_id": self.winner_id,
            "winner_name": self.winner_name,
            "total_hands": self.total_hands,
        }


# =============================================================================
# Hand Lifecycle
# =============================================================================


@dataclass(frozen=True, slots=True)
class HandStartedDetails:
    hand_number: int
    button_seat: Seat

    def to_dict(self) -> dict[str, Any]:
        return {
            "hand_number": self.hand_number,
            "button_seat": self.button_seat.value,
        }


@dataclass(frozen=True, slots=True)
class HoleCardDealtDetail:
    player_id: str
    player_name: str
    cards: Hand
    deal_order: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "cards": [card.to_dict() for card in self.cards.cards],
            "deal_order": self.deal_order,
        }


@dataclass(frozen=True, slots=True)
class HoleCardsDealtDetails:
    players: dict[str, HoleCardDealtDetail]

    def to_dict(self) -> dict[str, Any]:
        return {pid: detail.to_dict() for pid, detail in self.players.items()}


@dataclass(frozen=True, slots=True)
class BlindInfo:
    player_id: str
    player_name: str
    amount: ChipAmount

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "amount": self.amount.value,
        }


@dataclass(frozen=True, slots=True)
class BlindsPostedDetails:
    small_blind: BlindInfo
    big_blind: BlindInfo

    def to_dict(self) -> dict[str, Any]:
        return {
            "small_blind": self.small_blind.to_dict(),
            "big_blind": self.big_blind.to_dict(),
        }


# =============================================================================
# Betting Actions
# =============================================================================


@dataclass(frozen=True, slots=True)
class PlayerToActDetails:
    player_id: str
    player_name: str
    available_actions: list[ActionType]

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "available_actions": [action.value for action in self.available_actions],
        }


@dataclass(frozen=True, slots=True)
class ActionAppliedDetails:
    player_id: str
    player_name: str
    action_type: ActionType
    amount: ChipAmount | None
    narration: Narration | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "action_type": self.action_type.value,
            "amount": self.amount.value if self.amount else None,
            "narration": self.narration.to_dict() if self.narration else None,
        }


# =============================================================================
# Round Lifecycle
# =============================================================================


@dataclass(frozen=True, slots=True)
class RoundStartedDetails:
    phase: GamePhase
    new_cards: tuple[Card, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase.value,
            "new_cards": [card.to_dict() for card in self.new_cards],
        }


@dataclass(frozen=True, slots=True)
class RoundCompletedDetails:
    def to_dict(self) -> dict[str, Any]:
        return {}


# =============================================================================
# Hand Completion
# =============================================================================


@dataclass(frozen=True, slots=True)
class WinnerInfo:
    player_id: str
    player_name: str
    amount: ChipAmount
    pot_type: Literal["main", "side"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "amount": self.amount.value,
            "pot_type": self.pot_type,
        }


@dataclass(frozen=True, slots=True)
class EliminatedInfo:
    player_id: str
    player_name: str
    finish_position: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "finish_position": self.finish_position,
        }


@dataclass(frozen=True, slots=True)
class ShowdownInfo:
    player_id: str
    player_name: str
    cards: Hand
    hand_evaluation: HandEvaluation

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "cards": [card.to_dict() for card in self.cards.cards],
            "hand_evaluation": self.hand_evaluation.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class HandCompletedDetails:
    winners: list[WinnerInfo]
    eliminated: list[EliminatedInfo]
    showdown: list[ShowdownInfo] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "winners": [w.to_dict() for w in self.winners],
            "eliminated": [e.to_dict() for e in self.eliminated],
            "showdown": [s.to_dict() for s in self.showdown] if self.showdown else None,
        }
