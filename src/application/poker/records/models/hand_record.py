"""Hand record model - complete hand from deal to showdown."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.domain.models.blinds import BlindLevel
from src.domain.models.card import Card
from src.domain.models.game import GamePhase
from src.domain.models.seat import Seat

from .hand_outcome_record import HandOutcomeRecord
from .player_records import HandLevelPlayerRecord, RoundLevelPlayerRecord
from .round_record import RoundRecord


@dataclass(slots=True)
class HandRecord:
    hand_number: int
    button_seat: Seat
    blinds: BlindLevel
    player_records: dict[str, HandLevelPlayerRecord]
    rounds: list[RoundRecord] = field(default_factory=list)
    outcome: HandOutcomeRecord | None = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.hand_number < 1:
            raise ValueError(f"hand_number must be at least 1: {self.hand_number}")

    def start_round(
        self,
        phase: GamePhase,
        community_cards: tuple[Card, ...],
        player_records: dict[str, RoundLevelPlayerRecord],
    ) -> RoundRecord:
        round_record = RoundRecord(
            phase=phase,
            community_cards=community_cards,
            player_records=player_records,
        )
        self.rounds.append(round_record)
        return round_record

    def current_round(self) -> RoundRecord | None:
        return self.rounds[-1] if self.rounds else None

    def complete(self, outcome: HandOutcomeRecord) -> None:
        self.outcome = outcome
        self.completed_at = datetime.now()

        # Complete the last round if it's still in progress
        if self.rounds and not self.rounds[-1].is_complete:
            self.rounds[-1].complete()

    @property
    def is_complete(self) -> bool:
        return self.outcome is not None

    def to_dict(self) -> dict[str, Any]:
        """Serialize HandRecord to a dictionary."""
        return {
            "hand_number": self.hand_number,
            "button_seat": self.button_seat.value,
            "small_blind": self.blinds.small_blind.value,
            "big_blind": self.blinds.big_blind.value,
            "blind_level": self.blinds.level,
            "player_records": {
                player_id: record.to_dict() for player_id, record in self.player_records.items()
            },
            "rounds": [round.to_dict() for round in self.rounds],
            "outcome": self.outcome.to_dict() if self.outcome else None,
            "started_at": self.started_at.isoformat(),
            "completed_at": (self.completed_at.isoformat() if self.completed_at else None),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HandRecord:
        """Deserialize a dictionary to HandRecord."""
        from src.domain.models.chips import ChipAmount

        # Deserialize player records
        player_records: dict[str, HandLevelPlayerRecord] = {}
        player_records_data = data.get("player_records", {})
        for player_id, record_data in player_records_data.items():
            player_records[player_id] = HandLevelPlayerRecord.from_dict(record_data)

        hand = cls(
            hand_number=data["hand_number"],
            button_seat=Seat.from_int(data["button_seat"]),
            blinds=BlindLevel(
                small_blind=ChipAmount(data["small_blind"]),
                big_blind=ChipAmount(data["big_blind"]),
                level=data["blind_level"],
            ),
            player_records=player_records,
            started_at=datetime.fromisoformat(data["started_at"]),
        )

        # Deserialize rounds
        for round_data in data.get("rounds", []):
            hand.rounds.append(RoundRecord.from_dict(round_data))

        # Deserialize outcome
        outcome_data = data.get("outcome")
        if outcome_data:
            hand.outcome = HandOutcomeRecord.from_dict(outcome_data)
            completed_at = data.get("completed_at")
            if completed_at:
                hand.completed_at = datetime.fromisoformat(completed_at)

        return hand
