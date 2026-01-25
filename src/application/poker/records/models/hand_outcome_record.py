from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.application.poker.state_observers.details import (
    PlayerOutcome,
    ShowdownResult,
    WinnerInfo,
)
from src.domain.models.chips import ChipAmount

if TYPE_CHECKING:
    from src.application.poker.state_observers.details import (
        HandOutcomeDetails,
    )


@dataclass(frozen=True, slots=True)
class HandOutcomeRecord:
    winners: tuple[WinnerInfo, ...]
    showdown: tuple[ShowdownResult, ...] | None
    pot_amount: ChipAmount
    player_outcomes: tuple[PlayerOutcome, ...]

    def __post_init__(self) -> None:
        if not self.winners:
            raise ValueError("winners cannot be empty")
        if self.pot_amount.value <= 0:
            raise ValueError(
                f"pot_amount must be positive: {self.pot_amount.value}"
            )

    @classmethod
    def from_details(cls, details: HandOutcomeDetails) -> HandOutcomeRecord:
        return cls(
            winners=details.winners,
            showdown=details.showdown,
            pot_amount=details.pot_amount,
            player_outcomes=details.player_outcomes,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "winners": [w.to_dict() for w in self.winners],
            "showdown": (
                [s.to_dict() for s in self.showdown] if self.showdown else None
            ),
            "pot_amount": self.pot_amount.value,
            "player_outcomes": [p.to_dict() for p in self.player_outcomes],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HandOutcomeRecord:
        return cls(
            winners=tuple(WinnerInfo.from_dict(w) for w in data["winners"]),
            showdown=(
                tuple(ShowdownResult.from_dict(s) for s in data["showdown"])
                if data.get("showdown")
                else None
            ),
            pot_amount=ChipAmount(data["pot_amount"]),
            player_outcomes=tuple(
                PlayerOutcome.from_dict(p)
                for p in data.get("player_outcomes", [])
            ),
        )
