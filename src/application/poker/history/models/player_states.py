"""Player state snapshot models for tracking player state at each hierarchy level."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.domain.models.chips import ChipAmount
from src.domain.models.hand import Hand
from src.domain.models.player import HandParticipationStatus
from src.domain.models.position import PositionName
from src.domain.models.seat import Seat


@dataclass(frozen=True, slots=True)
class PlayerStateSnapshot:
    player_id: str
    player_name: str
    seat: Seat
    chips: ChipAmount

    def __post_init__(self) -> None:
        if not self.player_id:
            raise ValueError("player_id cannot be empty")
        if not self.player_name:
            raise ValueError("player_name cannot be empty")
        if self.chips.value < 0:
            raise ValueError(f"chips cannot be negative: {self.chips.value}")


@dataclass(frozen=True, slots=True)
class GameLevelPlayerState(PlayerStateSnapshot):
    hands_played: int = 0
    is_eliminated: bool = False
    elimination_hand_number: int | None = None
    table_finish_position: int | None = None

    def __post_init__(self) -> None:
        super(type(self), self).__post_init__()
        if self.hands_played < 0:
            raise ValueError(f"hands_played cannot be negative: {self.hands_played}")

    def to_dict(self) -> dict[str, Any]:
        """Serialize GameLevelPlayerState to a dictionary."""
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "seat": self.seat.value,
            "chips": self.chips.value,
            "hands_played": self.hands_played,
            "is_eliminated": self.is_eliminated,
            "elimination_hand_number": self.elimination_hand_number,
            "table_finish_position": self.table_finish_position,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GameLevelPlayerState:
        """Deserialize a dictionary to GameLevelPlayerState."""
        return cls(
            player_id=data["player_id"],
            player_name=data["player_name"],
            seat=Seat.from_int(data["seat"]),
            chips=ChipAmount(data["chips"]),
            hands_played=data.get("hands_played", 0),
            is_eliminated=data.get("is_eliminated", False),
            elimination_hand_number=data.get("elimination_hand_number"),
            table_finish_position=data.get("table_finish_position"),
        )


@dataclass(frozen=True, slots=True)
class HandLevelPlayerState(PlayerStateSnapshot):
    hole_cards: Hand | None
    position: PositionName | None
    starting_chips: ChipAmount
    total_invested_in_hand: ChipAmount = field(default_factory=lambda: ChipAmount(0))

    def __post_init__(self) -> None:
        super(HandLevelPlayerState, self).__post_init__()
        if self.total_invested_in_hand.value < 0:
            raise ValueError(
                f"total_invested_in_hand cannot be negative: {self.total_invested_in_hand.value}"
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize HandLevelPlayerState to a dictionary."""
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "seat": self.seat.value,
            "chips": self.chips.value,
            "hole_cards": (
                [self.hole_cards.card1.to_dict(), self.hole_cards.card2.to_dict()]
                if self.hole_cards
                else None
            ),
            "position": self.position.value if self.position else None,
            "starting_chips": self.starting_chips.value,
            "total_invested_in_hand": self.total_invested_in_hand.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HandLevelPlayerState:
        """Deserialize a dictionary to HandLevelPlayerState."""
        hole_cards = None
        if data.get("hole_cards"):
            from src.domain.models.card import Card

            hole_cards = Hand(
                card1=Card.from_dict(data["hole_cards"][0]),
                card2=Card.from_dict(data["hole_cards"][1]),
            )

        position = None
        if data.get("position"):
            position = PositionName(data["position"])

        return cls(
            player_id=data["player_id"],
            player_name=data["player_name"],
            seat=Seat.from_int(data["seat"]),
            chips=ChipAmount(data["chips"]),
            hole_cards=hole_cards,
            position=position,
            starting_chips=ChipAmount(data["starting_chips"]),
            total_invested_in_hand=ChipAmount(data.get("total_invested_in_hand", 0)),
        )


@dataclass(frozen=True, slots=True)
class RoundLevelPlayerState(PlayerStateSnapshot):
    chips_at_round_start: ChipAmount
    total_invested_in_hand: ChipAmount
    participation_status: HandParticipationStatus
    is_all_in: bool
    total_invested_in_round: ChipAmount = field(default_factory=lambda: ChipAmount(0))

    def __post_init__(self) -> None:
        super(type(self), self).__post_init__()
        if self.chips_at_round_start.value < 0:
            raise ValueError(
                f"chips_at_round_start cannot be negative: {self.chips_at_round_start.value}"
            )
        if self.total_invested_in_hand.value < 0:
            raise ValueError(
                f"total_invested_in_hand cannot be negative: {self.total_invested_in_hand.value}"
            )
        if self.total_invested_in_round.value < 0:
            raise ValueError(
                f"total_invested_in_round cannot be negative: {self.total_invested_in_round.value}"
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize RoundLevelPlayerState to a dictionary."""
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "seat": self.seat.value,
            "chips": self.chips.value,
            "chips_at_round_start": self.chips_at_round_start.value,
            "total_invested_in_hand": self.total_invested_in_hand.value,
            "total_invested_in_round": self.total_invested_in_round.value,
            "participation_status": self.participation_status.name,
            "is_all_in": self.is_all_in,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RoundLevelPlayerState:
        """Deserialize a dictionary to RoundLevelPlayerState."""
        participation_status = HandParticipationStatus[data["participation_status"]]

        return cls(
            player_id=data["player_id"],
            player_name=data["player_name"],
            seat=Seat.from_int(data["seat"]),
            chips=ChipAmount(data["chips"]),
            chips_at_round_start=ChipAmount(data["chips_at_round_start"]),
            total_invested_in_hand=ChipAmount(data["total_invested_in_hand"]),
            total_invested_in_round=ChipAmount(data.get("total_invested_in_round", 0)),
            participation_status=participation_status,
            is_all_in=data["is_all_in"],
        )


@dataclass(frozen=True, slots=True)
class TurnLevelPlayerState(PlayerStateSnapshot):
    total_invested_before_action: ChipAmount
    can_raise: bool

    def __post_init__(self) -> None:
        super(type(self), self).__post_init__()
        if self.total_invested_before_action.value < 0:
            raise ValueError(
                f"total_invested_before_action cannot be negative: {self.total_invested_before_action.value}"
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize TurnLevelPlayerState to a dictionary."""
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "seat": self.seat.value,
            "chips": self.chips.value,
            "total_invested_before_action": self.total_invested_before_action.value,
            "can_raise": self.can_raise,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TurnLevelPlayerState:
        """Deserialize a dictionary to TurnLevelPlayerState."""
        return cls(
            player_id=data["player_id"],
            player_name=data["player_name"],
            seat=Seat.from_int(data["seat"]),
            chips=ChipAmount(data["chips"]),
            total_invested_before_action=ChipAmount(data["total_invested_before_action"]),
            can_raise=data["can_raise"],
        )
