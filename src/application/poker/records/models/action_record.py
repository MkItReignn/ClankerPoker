from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.domain.models.actions import ActionType
from src.domain.models.chips import ChipAmount
from src.domain.models.game import GamePhase


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
        return cls(
            player_id=data["player_id"],
            player_name=data["player_name"],
            phase=GamePhase(data["phase"]),
            action_type=ActionType(data["action_type"]),
            amount=ChipAmount(data["amount"]) if data.get("amount") is not None else None,
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )
