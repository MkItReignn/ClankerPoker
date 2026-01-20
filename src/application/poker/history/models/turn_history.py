"""Turn history model - individual player action with complete context."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.domain.models.chips import ChipAmount
from src.domain.models.narration import Narration

from .outcomes import ActionRecord
from .player_states import TurnLevelPlayerState


@dataclass(frozen=True, slots=True)
class TurnHistory:
    turn_number: int
    player_state: TurnLevelPlayerState
    action: ActionRecord
    timestamp: datetime
    pot_before: ChipAmount
    pot_after: ChipAmount
    current_bet_before: ChipAmount
    current_bet_after: ChipAmount
    narration: Narration | None = None

    def __post_init__(self) -> None:
        if self.turn_number < 1:
            raise ValueError(f"turn_number must be at least 1: {self.turn_number}")
        if self.pot_before.value < 0:
            raise ValueError(f"pot_before cannot be negative: {self.pot_before.value}")
        if self.pot_after.value < 0:
            raise ValueError(f"pot_after cannot be negative: {self.pot_after.value}")
        if self.current_bet_before.value < 0:
            raise ValueError(
                f"current_bet_before cannot be negative: {self.current_bet_before.value}"
            )
        if self.current_bet_after.value < 0:
            raise ValueError(
                f"current_bet_after cannot be negative: {self.current_bet_after.value}"
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize TurnHistory to a dictionary."""
        return {
            "turn_number": self.turn_number,
            "player_state": self.player_state.to_dict(),
            "action": self.action.to_dict(),
            "timestamp": self.timestamp.isoformat(),
            "pot_before": self.pot_before.value,
            "pot_after": self.pot_after.value,
            "current_bet_before": self.current_bet_before.value,
            "current_bet_after": self.current_bet_after.value,
            "narration": self.narration.to_dict() if self.narration else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TurnHistory:
        """Deserialize a dictionary to TurnHistory."""
        player_state = TurnLevelPlayerState.from_dict(data["player_state"])
        action = ActionRecord.from_dict(data["action"])
        narration_data = data.get("narration")
        narration = Narration.from_dict(narration_data) if narration_data else None

        return cls(
            turn_number=data["turn_number"],
            player_state=player_state,
            action=action,
            timestamp=datetime.fromisoformat(data["timestamp"]),
            pot_before=ChipAmount(data["pot_before"]),
            pot_after=ChipAmount(data["pot_after"]),
            current_bet_before=ChipAmount(data["current_bet_before"]),
            current_bet_after=ChipAmount(data["current_bet_after"]),
            narration=narration,
        )
