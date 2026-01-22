from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.domain.models.actions import ActionType
from src.domain.models.chips import ChipAmount
from src.domain.models.game import GamePhase
from src.domain.models.hand import Hand
from src.domain.rules.hand_evaluator import HandEvaluation


@dataclass(frozen=True, slots=True)
class ActionRecord:
    player_id: str
    player_name: str
    phase: GamePhase
    action_type: ActionType
    amount: ChipAmount | None
    timestamp: datetime

    def __post_init__(self) -> None:
        if not self.player_id:
            raise ValueError("player_id cannot be empty")
        if not self.player_name:
            raise ValueError("player_name cannot be empty")

    def to_short_string(self) -> str:
        """Convert to shorthand notation (F, X, C, B100, R200, AI500, PSB10, PBB20)."""
        short = self.action_type.to_short_string()
        if self.amount is not None and self.action_type in (
            ActionType.BET,
            ActionType.RAISE,
            ActionType.ALL_IN,
            ActionType.POST_SMALL_BLIND,
            ActionType.POST_BIG_BLIND,
        ):
            return f"{short}{self.amount.value}"
        return short

    def to_dict(self) -> dict[str, Any]:
        """Serialize ActionRecord to a dictionary."""
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "phase": self.phase.value,
            "action_type": self.action_type.value,
            "amount": self.amount.value if self.amount else None,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActionRecord:
        """Deserialize a dictionary to ActionRecord."""
        return cls(
            player_id=data["player_id"],
            player_name=data["player_name"],
            phase=GamePhase(data["phase"]),
            action_type=ActionType(data["action_type"]),
            amount=ChipAmount(data["amount"]) if data.get("amount") is not None else None,
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


@dataclass(frozen=True, slots=True)
class ShowdownResult:
    player_id: str
    player_name: str
    hole_cards: Hand
    hand_evaluation: HandEvaluation

    def to_dict(self) -> dict[str, Any]:
        """Serialize ShowdownResult to a dictionary."""
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
        """Deserialize a dictionary to ShowdownResult."""
        from src.domain.models.card import Card

        # Handle legacy format (strings) for backward compatibility
        if "hole_cards" in data and isinstance(data["hole_cards"], str):
            raise ValueError(
                "Legacy showdown result format detected. Cannot deserialize string-based hole_cards."
            )

        hole_cards = Hand(
            card1=Card.from_dict(data["hole_cards"][0]),
            card2=Card.from_dict(data["hole_cards"][1]),
        )

        eval_data = data.get("hand_evaluation", {})
        # Handle legacy format where hand_description was a string
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
    was_eliminated: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize PlayerOutcome to a dictionary."""
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "chips_won": self.chips_won.value,
            "final_stack": self.final_stack.value,
            "was_eliminated": self.was_eliminated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlayerOutcome:
        """Deserialize a dictionary to PlayerOutcome."""
        return cls(
            player_id=data["player_id"],
            player_name=data["player_name"],
            chips_won=ChipAmount(data["chips_won"]),
            final_stack=ChipAmount(data["final_stack"]),
            was_eliminated=data.get("was_eliminated", False),
        )


@dataclass(frozen=True, slots=True)
class HandOutcome:
    winner_ids: tuple[str, ...]
    pot_amount: ChipAmount
    was_showdown: bool
    showdown_results: tuple[ShowdownResult, ...] = ()
    player_outcomes: tuple[PlayerOutcome, ...] = ()

    def __post_init__(self) -> None:
        if not self.winner_ids:
            raise ValueError("winner_ids cannot be empty")
        if self.pot_amount.value <= 0:
            raise ValueError(f"pot_amount must be positive: {self.pot_amount.value}")

    def to_dict(self) -> dict[str, Any]:
        """Serialize HandOutcome to a dictionary."""
        return {
            "winner_ids": list(self.winner_ids),
            "pot_amount": self.pot_amount.value,
            "was_showdown": self.was_showdown,
            "showdown_results": [sr.to_dict() for sr in self.showdown_results],
            "player_outcomes": [po.to_dict() for po in self.player_outcomes],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HandOutcome:
        """Deserialize a dictionary to HandOutcome."""
        showdown_results = tuple(
            ShowdownResult.from_dict(sr) for sr in data.get("showdown_results", [])
        )

        player_outcomes = tuple(
            PlayerOutcome.from_dict(po) for po in data.get("player_outcomes", [])
        )

        return cls(
            winner_ids=tuple(data["winner_ids"]),
            pot_amount=ChipAmount(data["pot_amount"]),
            was_showdown=data["was_showdown"],
            showdown_results=showdown_results,
            player_outcomes=player_outcomes,
        )
