from __future__ import annotations

from src.application.poker.state_observers.details import (
    ActionAppliedDetails, BlindsPostedDetails, GameCompletedDetails,
    GameStartedDetails, HandCompletedDetails, HandStartedDetails,
    HoleCardsDealtDetails, PlayerToActDetails, RoundCompletedDetails,
    RoundStartedDetails)
from src.application.poker.state_observers.protocol import GameStateObserver
from src.domain.models.game import Game


class GameStateNotifier:
    """Composite pattern - notifies all observers of state changes."""

    def __init__(self, observers: list[GameStateObserver]) -> None:
        self._observers = observers

    async def on_game_started(self, game: Game, details: GameStartedDetails) -> None:
        for observer in self._observers:
            await observer.on_game_started(game, details)

    async def on_game_completed(self, game: Game, details: GameCompletedDetails) -> None:
        for observer in self._observers:
            await observer.on_game_completed(game, details)

    async def on_hand_started(self, game: Game, details: HandStartedDetails) -> None:
        for observer in self._observers:
            await observer.on_hand_started(game, details)

    async def on_hand_completed(self, game: Game, details: HandCompletedDetails) -> None:
        for observer in self._observers:
            await observer.on_hand_completed(game, details)

    async def on_round_started(self, game: Game, details: RoundStartedDetails) -> None:
        for observer in self._observers:
            await observer.on_round_started(game, details)

    async def on_round_completed(self, game: Game, details: RoundCompletedDetails) -> None:
        for observer in self._observers:
            await observer.on_round_completed(game, details)

    async def on_blinds_posted(self, game: Game, details: BlindsPostedDetails) -> None:
        for observer in self._observers:
            await observer.on_blinds_posted(game, details)

    async def on_action_applied(self, game: Game, details: ActionAppliedDetails) -> None:
        for observer in self._observers:
            await observer.on_action_applied(game, details)

    async def on_hole_cards_dealt(self, game: Game, details: HoleCardsDealtDetails) -> None:
        for observer in self._observers:
            await observer.on_hole_cards_dealt(game, details)

    async def on_player_to_act(self, game: Game, details: PlayerToActDetails) -> None:
        for observer in self._observers:
            await observer.on_player_to_act(game, details)
