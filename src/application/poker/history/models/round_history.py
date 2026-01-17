"""Round history model - betting phase within a hand."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.domain.models.card import Card
from src.domain.models.game import GamePhase

from .player_states import RoundLevelPlayerState
from .turn_history import TurnHistory


@dataclass(slots=True)
class RoundHistory:
    phase: GamePhase
    community_cards: tuple[Card, ...]
    player_states: dict[str, RoundLevelPlayerState]
    turns: list[TurnHistory] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        if len(self.community_cards) not in (0, 5):
            raise ValueError(
                f"community_cards must be 0 or 5 cards, got {len(self.community_cards)}"
            )

    def add_turn(self, turn: TurnHistory) -> None:
        self.turns.append(turn)

    def complete(self) -> None:
        self.completed_at = datetime.now()

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None

    def get_actions_by_player(self, player_id: str) -> list[TurnHistory]:
        return [turn for turn in self.turns if turn.player_state.player_id == player_id]

    def get_turn_count(self) -> int:
        return len(self.turns)

    def to_dict(self) -> dict[str, Any]:
        """Serialize RoundHistory to a dictionary."""
        return {
            "phase": self.phase.value,
            "community_cards": [card.to_dict() for card in self.community_cards],
            "player_states": {
                player_id: state.to_dict() for player_id, state in self.player_states.items()
            },
            "turns": [turn.to_dict() for turn in self.turns],
            "started_at": self.started_at.isoformat(),
            "completed_at": (self.completed_at.isoformat() if self.completed_at else None),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RoundHistory:
        """Deserialize a dictionary to RoundHistory."""
        # Deserialize player states
        player_states: dict[str, RoundLevelPlayerState] = {}
        for player_id, state_data in data.get("player_states", {}).items():
            player_states[player_id] = RoundLevelPlayerState.from_dict(state_data)

        # Deserialize community cards
        community_cards = tuple(
            Card.from_dict(card_data) for card_data in data.get("community_cards", [])
        )

        round_history = cls(
            phase=GamePhase(data["phase"]),
            community_cards=community_cards,
            player_states=player_states,
            started_at=datetime.fromisoformat(data["started_at"]),
        )

        # Deserialize turns
        for turn_data in data.get("turns", []):
            round_history.turns.append(TurnHistory.from_dict(turn_data))

        # Set completed_at if present
        if data.get("completed_at"):
            round_history.completed_at = datetime.fromisoformat(data["completed_at"])

        return round_history
