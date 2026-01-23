from src.application.poker.state_observers.details import (
    ActionAppliedDetails,
    BlindsPostedDetails,
    GameCompletedDetails,
    GameStartedDetails,
    HandCompletedDetails,
    HandStartedDetails,
    HoleCardsDealtDetails,
    PlayerToActDetails,
    RoundCompletedDetails,
    RoundStartedDetails,
)
from src.application.poker.state_observers.details_factory import (
    DetailsFactory,
    HasActionFields,
)
from src.application.poker.state_observers.protocol import GameStateObserver
from src.domain.models.game import Game


class GameStateNotifier:
    """Composite pattern - notifies all observers of state changes.

    Accepts raw parameters from StateManager, uses DetailsFactory to derive
    Details objects, and passes them to observers.
    """

    def __init__(self, observers: list[GameStateObserver]) -> None:
        self._observers: list[GameStateObserver] = observers

    async def on_game_started(self, game: Game) -> None:
        details: GameStartedDetails = DetailsFactory.game_started(game)
        for observer in self._observers:
            await observer.on_game_started(game, details)

    async def on_game_completed(self, game: Game) -> None:
        details: GameCompletedDetails = DetailsFactory.game_completed(game)
        for observer in self._observers:
            await observer.on_game_completed(game, details)

    async def on_hand_started(self, game: Game) -> None:
        details: HandStartedDetails = DetailsFactory.hand_started(game)
        for observer in self._observers:
            await observer.on_hand_started(game, details)

    async def on_hand_completed(self, game: Game) -> None:
        details: HandCompletedDetails = DetailsFactory.hand_completed(game)
        for observer in self._observers:
            await observer.on_hand_completed(game, details)

    async def on_round_started(self, game: Game) -> None:
        details: RoundStartedDetails = DetailsFactory.round_started(game)
        for observer in self._observers:
            await observer.on_round_started(game, details)

    async def on_round_completed(self, game: Game) -> None:
        details: RoundCompletedDetails = DetailsFactory.round_completed()
        for observer in self._observers:
            await observer.on_round_completed(game, details)

    async def on_blinds_posted(self, game: Game) -> None:
        details: BlindsPostedDetails = DetailsFactory.blinds_posted(game)
        for observer in self._observers:
            await observer.on_blinds_posted(game, details)

    async def on_hole_cards_dealt(self, game: Game) -> None:
        details: HoleCardsDealtDetails = DetailsFactory.hole_cards_dealt(game)
        for observer in self._observers:
            await observer.on_hole_cards_dealt(game, details)

    async def on_player_to_act(self, game: Game) -> None:
        details: PlayerToActDetails = DetailsFactory.player_to_act(game)
        for observer in self._observers:
            await observer.on_player_to_act(game, details)

    async def on_action_applied(
        self, game: Game, player_id: str, response: HasActionFields
    ) -> None:
        details: ActionAppliedDetails = DetailsFactory.action_applied(game, player_id, response)
        for observer in self._observers:
            await observer.on_action_applied(game, details)
