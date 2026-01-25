"""Round record model - betting phase within a hand."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Self

from src.domain.models.card import Card
from src.domain.models.game import HandPhase

from .player_records import RoundLevelPlayerRecord
from .turn_record import TurnRecord


@dataclass(slots=True)
class RoundRecord:
    phase: HandPhase
    community_cards: tuple[Card, ...]
    player_records: dict[str, RoundLevelPlayerRecord]
    turns: list[TurnRecord] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        if len(self.community_cards) not in (0, 3, 4, 5):
            raise ValueError(
                f"community_cards must be 0, 3, 4, or 5 cards, got {len(self.community_cards)}"
            )

    def add_turn(self, turn: TurnRecord) -> None:
        self.turns.append(turn)

    def complete(self) -> None:
        self.completed_at = datetime.now()

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None

    def to_dict(self) -> dict[str, Any]:
        """Serialize RoundRecord to a dictionary."""
        return {
            "phase": self.phase.value,
            "community_cards": [
                card.to_dict() for card in self.community_cards
            ],
            "player_records": {
                player_id: record.to_dict()
                for player_id, record in self.player_records.items()
            },
            "turns": [turn.to_dict() for turn in self.turns],
            "started_at": self.started_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Deserialize a dictionary to RoundRecord."""
        # Deserialize player records
        player_records: dict[str, RoundLevelPlayerRecord] = {}
        for player_id, record_data in data.get("player_records", {}).items():
            player_records[player_id] = RoundLevelPlayerRecord.from_dict(
                record_data
            )

        # Deserialize community cards
        community_cards = tuple(
            Card.from_dict(card_data)
            for card_data in data.get("community_cards", [])
        )

        round_record = cls(
            phase=HandPhase(data["phase"]),
            community_cards=community_cards,
            player_records=player_records,
            started_at=datetime.fromisoformat(data["started_at"]),
        )

        # Deserialize turns
        for turn_data in data.get("turns", []):
            round_record.turns.append(TurnRecord.from_dict(turn_data))

        # Set completed_at if present
        if data.get("completed_at"):
            round_record.completed_at = datetime.fromisoformat(
                data["completed_at"]
            )

        return round_record
