from __future__ import annotations

from typing import Protocol

from src.application.poker.state_observers.details import (
    HandOutcomeDetails,
    ActionAppliedDetails,
    BlindsPostedDetails,
    GameCompletedDetails,
    GameStartedDetails,
    HandStartedDetails,
    HoleCardsDealtDetails,
    PlayerToActDetails,
    RoundCompletedDetails,
    RoundStartedDetails,
)
from src.domain.models.game import Game


class GameStateObserver(Protocol):
    async def on_game_started(self, game: Game, details: GameStartedDetails) -> None: ...

    async def on_game_completed(self, game: Game, details: GameCompletedDetails) -> None: ...

    async def on_hand_started(self, game: Game, details: HandStartedDetails) -> None: ...

    async def on_hand_completed(self, game: Game, details: HandOutcomeDetails) -> None: ...

    async def on_round_started(self, game: Game, details: RoundStartedDetails) -> None: ...

    async def on_round_completed(self, game: Game, details: RoundCompletedDetails) -> None: ...

    async def on_blinds_posted(self, game: Game, details: BlindsPostedDetails) -> None: ...

    async def on_action_applied(self, game: Game, details: ActionAppliedDetails) -> None: ...

    async def on_hole_cards_dealt(self, game: Game, details: HoleCardsDealtDetails) -> None: ...

    async def on_player_to_act(self, game: Game, details: PlayerToActDetails) -> None: ...
