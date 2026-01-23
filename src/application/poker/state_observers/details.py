from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
# Hand Outcome Details
# =============================================================================


@dataclass(frozen=True, slots=True)
class WinnerInfo:
    player_id: str
    player_name: str
    amount: ChipAmount

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "amount": self.amount.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WinnerInfo:
        return cls(
            player_id=data["player_id"],
            player_name=data["player_name"],
            amount=ChipAmount(data["amount"]),
        )


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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EliminatedInfo:
        return cls(
            player_id=data["player_id"],
            player_name=data["player_name"],
            finish_position=data["finish_position"],
        )


@dataclass(frozen=True, slots=True)
class ShowdownResult:
    player_id: str
    player_name: str
    hole_cards: Hand
    hand_evaluation: HandEvaluation

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "hole_cards": [
                self.hole_cards.card1.to_dict(),
                self.hole_cards.card2.to_dict(),
            ],
            "hand_evaluation": self.hand_evaluation.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ShowdownResult:
        if "hole_cards" in data and isinstance(data["hole_cards"], str):
            raise ValueError(
                "Legacy showdown result format detected. Cannot deserialize string-based hole_cards."
            )

        hole_cards = Hand(
            card1=Card.from_dict(data["hole_cards"][0]),
            card2=Card.from_dict(data["hole_cards"][1]),
        )

        eval_data = data.get("hand_evaluation", {})
        if "hand_description" in data and "hand_evaluation" not in data:
            raise ValueError(
                "Legacy showdown result format detected. Cannot deserialize string-based hand_description."
            )

        hand_evaluation = HandEvaluation.from_dict(eval_data)

        return cls(
            player_id=data["player_id"],
            player_name=data["player_name"],
            hole_cards=hole_cards,
            hand_evaluation=hand_evaluation,
        )


@dataclass(frozen=True, slots=True)
class PlayerOutcome:
    player_id: str
    player_name: str
    chips_won: ChipAmount
    final_stack: ChipAmount

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "chips_won": self.chips_won.value,
            "final_stack": self.final_stack.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlayerOutcome:
        return cls(
            player_id=data["player_id"],
            player_name=data["player_name"],
            chips_won=ChipAmount(data["chips_won"]),
            final_stack=ChipAmount(data["final_stack"]),
        )


@dataclass(frozen=True, slots=True)
class HandOutcomeDetails:
    winners: tuple[WinnerInfo, ...]
    eliminated: tuple[EliminatedInfo, ...]
    showdown: tuple[ShowdownResult, ...] | None
    pot_amount: ChipAmount
    player_outcomes: tuple[PlayerOutcome, ...]

    def __post_init__(self) -> None:
        if not self.winners:
            raise ValueError("winners cannot be empty")
        if self.pot_amount.value <= 0:
            raise ValueError(f"pot_amount must be positive: {self.pot_amount.value}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "winners": [w.to_dict() for w in self.winners],
            "eliminated": [e.to_dict() for e in self.eliminated],
            "showdown": [s.to_dict() for s in self.showdown] if self.showdown else None,
            "pot_amount": self.pot_amount.value,
            "player_outcomes": [p.to_dict() for p in self.player_outcomes],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HandOutcomeDetails:
        return cls(
            winners=tuple(WinnerInfo.from_dict(w) for w in data["winners"]),
            eliminated=tuple(EliminatedInfo.from_dict(e) for e in data.get("eliminated", [])),
            showdown=(
                tuple(ShowdownResult.from_dict(s) for s in data["showdown"])
                if data.get("showdown")
                else None
            ),
            pot_amount=ChipAmount(data["pot_amount"]),
            player_outcomes=tuple(
                PlayerOutcome.from_dict(p) for p in data.get("player_outcomes", [])
            ),
        )


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
