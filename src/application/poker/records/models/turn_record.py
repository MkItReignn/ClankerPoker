"""Turn record model - individual player action."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.domain.models.narration import Narration

from .outcomes import ActionRecord


@dataclass(frozen=True, slots=True)
class TurnRecord:
    round_turn_number: int
    action: ActionRecord
    timestamp: datetime
    narration: Narration | None = None

    def __post_init__(self) -> None:
        if self.round_turn_number < 1:
            raise ValueError(f"round_turn_number must be at least 1: {self.round_turn_number}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_turn_number": self.round_turn_number,
            "action": self.action.to_dict(),
            "timestamp": self.timestamp.isoformat(),
            "narration": self.narration.to_dict() if self.narration else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TurnRecord:
        action = ActionRecord.from_dict(data["action"])
        narration_data = data.get("narration")
        narration = Narration.from_dict(narration_data) if narration_data else None

        return cls(
            round_turn_number=data["round_turn_number"],
            action=action,
            timestamp=datetime.fromisoformat(data["timestamp"]),
            narration=narration,
        )
