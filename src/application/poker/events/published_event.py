from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


class EventType(StrEnum):
    GAME_STARTED = "game_started"
    GAME_COMPLETED = "game_completed"
    HAND_STARTED = "hand_started"
    HAND_COMPLETED = "hand_completed"
    ROUND_STARTED = "round_started"
    ROUND_COMPLETED = "round_completed"
    BLINDS_POSTED = "blinds_posted"
    ACTION_APPLIED = "action_applied"
    HOLE_CARDS_DEALT = "hole_cards_dealt"
    PLAYER_TO_ACT = "player_to_act"


@dataclass(frozen=True, slots=True)
class PublishedEventMetadata:
    game_id: str
    hand_number: int
    timestamp: datetime
    sequence: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "game_id": self.game_id,
            "hand_number": self.hand_number,
            "timestamp": self.timestamp.isoformat(),
            "sequence": self.sequence,
        }


@dataclass(frozen=True, slots=True)
class PublishedEvent:
    """Transport envelope for real-time UI updates.

    Combines event semantics (type + details) with state snapshot (game_state).
    This is what the Publisher produces for transport to frontends.
    """

    event_type: EventType
    details: dict[str, Any]
    game_state: dict[str, Any]
    metadata: PublishedEventMetadata

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "details": self.details,
            "game_state": self.game_state,
            "metadata": self.metadata.to_dict(),
        }
