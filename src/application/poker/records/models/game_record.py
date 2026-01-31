"""Game record model - complete tournament/session."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Self

from src.application.poker.state_observers.details import HandOutcomeDetails
from src.config.blind_schedule.config import BlindSchedule, BlindScheduleEntry
from src.config.tournament.config import PayoutStructure
from src.domain.models.blinds import BlindLevel
from src.domain.models.chips import ChipAmount
from src.domain.models.game import Game
from src.domain.models.llm_model import LlmModel
from src.domain.models.player import UNDETERMINED_FINISH_POSITION
from src.domain.models.seat import Seat

from .hand_outcome_record import HandOutcomeRecord
from .hand_record import HandRecord
from .player_records import (
    GameLevelPlayerRecord,
    HandLevelPlayerRecord,
    PlayerConfig,
)

DEFAULT_HAND_HISTORY_COUNT = 5


@dataclass(slots=True)
class GameMetadata:
    seed: int
    buy_in_amount: ChipAmount
    starting_chip_stack: ChipAmount
    blind_schedule: BlindSchedule
    payout_structure: PayoutStructure
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize GameMetadata to a dictionary."""
        return {
            "seed": self.seed,
            "buy_in_amount": self.buy_in_amount.value,
            "starting_chip_stack": self.starting_chip_stack.value,
            "blind_schedule": [
                {
                    "level": entry.level.level,
                    "small_blind": entry.level.small_blind.value,
                    "big_blind": entry.level.big_blind.value,
                    "start_hand": entry.start_hand,
                    "duration_hands": entry.duration_hands,
                }
                for entry in self.blind_schedule.entries
            ],
            "payout_structure": self.payout_structure.value,
            "started_at": (
                self.started_at.isoformat() if self.started_at else None
            ),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Deserialize a dictionary to GameMetadata."""
        from src.domain.models.blinds import BlindLevel

        # Deserialize blind schedule
        entries = tuple(
            BlindScheduleEntry(
                level=BlindLevel(
                    small_blind=ChipAmount(entry["small_blind"]),
                    big_blind=ChipAmount(entry["big_blind"]),
                    level=entry["level"],
                ),
                start_hand=entry["start_hand"],
                duration_hands=entry["duration_hands"],
            )
            for entry in data["blind_schedule"]
        )
        blind_schedule = BlindSchedule(entries=entries)

        # Deserialize timestamps
        started_at = None
        if data.get("started_at"):
            started_at = datetime.fromisoformat(data["started_at"])

        completed_at = None
        if data.get("completed_at"):
            completed_at = datetime.fromisoformat(data["completed_at"])

        return cls(
            seed=data["seed"],
            buy_in_amount=ChipAmount(data["buy_in_amount"]),
            starting_chip_stack=ChipAmount(data["starting_chip_stack"]),
            blind_schedule=blind_schedule,
            payout_structure=PayoutStructure(data["payout_structure"]),
            started_at=started_at,
            completed_at=completed_at,
        )

    @classmethod
    def from_game(cls, game: Game) -> Self:
        return cls(
            seed=game.identity.seed,
            buy_in_amount=game.tournament_config.buy_in_amount,
            starting_chip_stack=game.tournament_config.starting_chip_stack,
            blind_schedule=game.tournament_config.blind_schedule,
            payout_structure=game.tournament_config.payout_structure,
            started_at=game.identity.started_at,
            completed_at=game.identity.completed_at,
        )


@dataclass(slots=True)
class GameRecord:
    game_id: str
    metadata: GameMetadata
    player_records: dict[str, GameLevelPlayerRecord] = field(
        default_factory=dict
    )
    completed_hands: list[HandRecord] = field(default_factory=list)
    current_hand: HandRecord | None = None
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.game_id:
            raise ValueError("game_id cannot be empty")

    def register_player(
        self,
        player_id: str,
        name: str,
        seat: Seat,
        llm_model: LlmModel,
        player_config: PlayerConfig,
    ) -> None:
        self.player_records[player_id] = GameLevelPlayerRecord(
            player_id=player_id,
            player_name=name,
            seat=seat,
            chips=self.metadata.starting_chip_stack,
            llm_model=llm_model,
            player_config=player_config,
            hands_played=0,
            is_eliminated=False,
            elimination_hand_number=None,
            table_finish_position=UNDETERMINED_FINISH_POSITION,
        )

    def start_hand(
        self,
        hand_number: int,
        button_seat: Seat,
        blinds: BlindLevel,
        player_records: dict[str, HandLevelPlayerRecord],
    ) -> HandRecord:
        if self.current_hand is not None and not self.current_hand.is_complete:
            raise ValueError(
                "Cannot start new hand while previous hand is incomplete"
            )

        self.current_hand = HandRecord(
            hand_number=hand_number,
            button_seat=button_seat,
            blinds=blinds,
            player_records=player_records,
        )
        return self.current_hand

    def complete_hand(self, outcome: HandOutcomeDetails) -> None:
        if self.current_hand is None:
            raise ValueError("No current hand to complete")

        hand_outcome_record = HandOutcomeRecord.from_details(outcome)
        self.current_hand.complete(hand_outcome_record)
        self.completed_hands.append(self.current_hand)

        eliminated_positions: dict[str, int] = {
            e.player_id: e.finish_position
            for e in outcome.eliminated
        }

        for player_outcome in outcome.player_outcomes:
            if player_outcome.player_id in self.player_records:
                old_record = self.player_records[player_outcome.player_id]
                was_eliminated = (
                    player_outcome.player_id in eliminated_positions
                )
                self.player_records[player_outcome.player_id] = (
                    GameLevelPlayerRecord(
                        player_id=old_record.player_id,
                        player_name=old_record.player_name,
                        seat=old_record.seat,
                        chips=player_outcome.final_stack,
                        llm_model=old_record.llm_model,
                        player_config=old_record.player_config,
                        hands_played=old_record.hands_played + 1,
                        is_eliminated=was_eliminated,
                        elimination_hand_number=(
                            self.current_hand.hand_number
                            if was_eliminated
                            else old_record.elimination_hand_number
                        ),
                        table_finish_position=(
                            eliminated_positions[
                                player_outcome.player_id
                            ]
                            if was_eliminated
                            else old_record.table_finish_position
                        ),
                    )
                )

        self.current_hand = None

    def get_last_hand_records(
        self, count: int = DEFAULT_HAND_HISTORY_COUNT
    ) -> list[HandRecord]:
        return list(reversed(self.completed_hands[-count:]))

    def to_dict(self) -> dict[str, Any]:
        """Serialize GameRecord to a dictionary."""
        return {
            "game_id": self.game_id,
            "seed": self.metadata.seed,
            "buy_in_amount": self.metadata.buy_in_amount.value,
            "starting_chip_stack": self.metadata.starting_chip_stack.value,
            "blind_schedule": [
                {
                    "level": entry.level.level,
                    "small_blind": entry.level.small_blind.value,
                    "big_blind": entry.level.big_blind.value,
                    "start_hand": entry.start_hand,
                    "duration_hands": entry.duration_hands,
                }
                for entry in self.metadata.blind_schedule.entries
            ],
            "payout_structure": self.metadata.payout_structure.value,
            "started_at": (
                self.metadata.started_at.isoformat()
                if self.metadata.started_at
                else None
            ),
            "completed_at": (
                self.metadata.completed_at.isoformat()
                if self.metadata.completed_at
                else None
            ),
            "player_records": {
                player_id: record.to_dict()
                for player_id, record in self.player_records.items()
            },
            "completed_hands": [
                hand.to_dict() for hand in self.completed_hands
            ],
            "current_hand": (
                self.current_hand.to_dict() if self.current_hand else None
            ),
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Deserialize a dictionary to GameRecord."""
        # Reconstruct metadata dict for from_dict
        metadata_dict = {
            "seed": data["seed"],
            "buy_in_amount": data["buy_in_amount"],
            "starting_chip_stack": data["starting_chip_stack"],
            "blind_schedule": data["blind_schedule"],
            "payout_structure": data["payout_structure"],
            "started_at": data.get("started_at"),
            "completed_at": data.get("completed_at"),
        }
        metadata = GameMetadata.from_dict(metadata_dict)

        record = cls(
            game_id=data["game_id"],
            metadata=metadata,
            created_at=datetime.fromisoformat(data["created_at"]),
        )

        # Deserialize player records
        player_records_data = data.get("player_records", {})
        for player_id, record_data in player_records_data.items():
            record.player_records[player_id] = GameLevelPlayerRecord.from_dict(
                record_data
            )

        # Deserialize completed hands
        for hand_data in data.get("completed_hands", []):
            hand = HandRecord.from_dict(hand_data)
            record.completed_hands.append(hand)

        # Deserialize current hand
        current_hand_data = data.get("current_hand")
        if current_hand_data:
            record.current_hand = HandRecord.from_dict(current_hand_data)

        return record
