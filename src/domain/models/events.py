from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.domain.models.actions import Action
from src.domain.models.narration import Narration

EventId = str


class GameEventType(Enum):
    # Game lifecycle
    GAME_CREATED = "game_created"
    GAME_STARTED = "game_started"
    GAME_COMPLETED = "game_completed"
    GAME_CANCELLED = "game_cancelled"

    # Hand lifecycle
    BLINDS_POSTED = "blinds_posted"
    CARDS_DEALT = "cards_dealt"
    PHASE_STARTED = "phase_started"
    ACTION_TAKEN = "action_taken"
    ROUND_COMPLETE = "round_complete"
    SHOWDOWN_STARTED = "showdown_started"
    HAND_COMPLETE = "hand_complete"
    POT_DISTRIBUTED = "pot_distributed"
    SIDE_POT_CREATED = "side_pot_created"

    # Game progression
    BLIND_LEVEL_INCREASED = "blind_level_increased"
    PLAYER_ELIMINATED = "player_eliminated"


@dataclass(frozen=True, slots=True)
class GameEvent:
    id: EventId
    game_id: str
    event_type: GameEventType
    occurred_at: datetime
    player_id: str | None
    action: Action | None
    narration: Narration | None
    metadata: dict[str, object]

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Event id cannot be empty")
        if not self.game_id:
            raise ValueError("Game id cannot be empty")
        if self.event_type == GameEventType.ACTION_TAKEN:
            if self.action is None:
                raise ValueError("ACTION_TAKEN event must have an action")
            if self.player_id is None:
                raise ValueError("ACTION_TAKEN event must have a player_id")
        if self.narration is not None and self.action is None:
            raise ValueError("Narration can only be present with an action")
