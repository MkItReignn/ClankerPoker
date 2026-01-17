"""Hand history model - complete hand from deal to showdown."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.domain.models.blinds import BlindLevel
from src.domain.models.card import Card
from src.domain.models.game import GamePhase
from src.domain.models.seat import Seat

from .outcomes import HandOutcome
from .player_states import HandLevelPlayerState, RoundLevelPlayerState
from .round_history import RoundHistory
from .turn_history import TurnHistory


@dataclass(slots=True)
class HandHistory:
    hand_number: int
    button_seat: Seat
    blinds: BlindLevel
    player_states: dict[str, HandLevelPlayerState]
    rounds: list[RoundHistory] = field(default_factory=list)
    outcome: HandOutcome | None = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.hand_number < 1:
            raise ValueError(f"hand_number must be at least 1: {self.hand_number}")

    def start_round(
        self,
        phase: GamePhase,
        community_cards: tuple[Card, ...],
        player_states: dict[str, RoundLevelPlayerState],
    ) -> RoundHistory:
        round_history = RoundHistory(
            phase=phase,
            community_cards=community_cards,
            player_states=player_states,
        )
        self.rounds.append(round_history)
        return round_history

    def current_round(self) -> RoundHistory | None:
        return self.rounds[-1] if self.rounds else None

    def complete(self, outcome: HandOutcome) -> None:
        self.outcome = outcome
        self.completed_at = datetime.now()

        # Complete the last round if it's still in progress
        if self.rounds and not self.rounds[-1].is_complete:
            self.rounds[-1].complete()

    @property
    def is_complete(self) -> bool:
        return self.outcome is not None

    def get_round_by_phase(self, phase: GamePhase) -> RoundHistory | None:
        for round_history in self.rounds:
            if round_history.phase == phase:
                return round_history
        return None

    def get_all_turns(self) -> list[TurnHistory]:
        turns: list[TurnHistory] = []
        for round_history in self.rounds:
            turns.extend(round_history.turns)
        return turns

    def get_player_turns(self, player_id: str) -> list[TurnHistory]:
        turns: list[TurnHistory] = []
        for round_history in self.rounds:
            turns.extend(round_history.get_actions_by_player(player_id))
        return turns

    def to_dict(self) -> dict[str, Any]:
        """Serialize HandHistory to a dictionary."""
        return {
            "hand_number": self.hand_number,
            "button_seat": self.button_seat.value,
            "small_blind": self.blinds.small_blind.value,
            "big_blind": self.blinds.big_blind.value,
            "blind_level": self.blinds.level,
            "player_states": {
                player_id: state.to_dict() for player_id, state in self.player_states.items()
            },
            "rounds": [round.to_dict() for round in self.rounds],
            "outcome": self.outcome.to_dict() if self.outcome else None,
            "started_at": self.started_at.isoformat(),
            "completed_at": (self.completed_at.isoformat() if self.completed_at else None),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HandHistory:
        """Deserialize a dictionary to HandHistory."""
        from src.domain.models.chips import ChipAmount

        # Deserialize player states
        player_states: dict[str, HandLevelPlayerState] = {}
        player_states_data = data.get("player_states", {})
        for player_id, state_data in player_states_data.items():
            player_states[player_id] = HandLevelPlayerState.from_dict(state_data)

        hand = cls(
            hand_number=data["hand_number"],
            button_seat=Seat.from_int(data["button_seat"]),
            blinds=BlindLevel(
                small_blind=ChipAmount(data["small_blind"]),
                big_blind=ChipAmount(data["big_blind"]),
                level=data.get("blind_level", 1),  # Default to 1 for old data
            ),
            player_states=player_states,
            started_at=datetime.fromisoformat(data["started_at"]),
        )

        # Deserialize rounds
        for round_data in data.get("rounds", []):
            hand.rounds.append(RoundHistory.from_dict(round_data))

        # Deserialize outcome
        outcome_data = data.get("outcome")
        if outcome_data:
            hand.outcome = HandOutcome.from_dict(outcome_data)
            completed_at = data.get("completed_at")
            if completed_at:
                hand.completed_at = datetime.fromisoformat(completed_at)

        return hand
