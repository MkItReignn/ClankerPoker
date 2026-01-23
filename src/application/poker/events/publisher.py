from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from src.application.poker.events.published_event import (
    EventType,
    PublishedEvent,
    PublishedEventMetadata,
)
from src.application.poker.state_observers.details import (
    ActionAppliedDetails,
    BlindsPostedDetails,
    GameCompletedDetails,
    GameStartedDetails,
    HandOutcomeDetails,
    HandStartedDetails,
    HoleCardsDealtDetails,
    PlayerToActDetails,
    RoundCompletedDetails,
    RoundStartedDetails,
)
from src.domain.models.game import Game


class EventTransport(Protocol):
    async def publish(self, event: PublishedEvent) -> None: ...


class EventPublisher:
    """Publishes game events to a transport for real-time UI updates.

    Implements GameStateObserver protocol. Creates PublishedEvent instances
    combining event details with game state snapshots.
    """

    def __init__(self, transport: EventTransport) -> None:
        self._transport = transport
        self._sequence = 0

    def _next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence

    def _create_event(
        self,
        event_type: EventType,
        game: Game,
        details: dict,
    ) -> PublishedEvent:
        metadata = PublishedEventMetadata(
            game_id=game.id,
            hand_number=game.hand_state.hand_number,
            timestamp=datetime.now(timezone.utc),
            sequence=self._next_sequence(),
        )
        return PublishedEvent(
            event_type=event_type,
            details=details,
            game_state=game.to_dict(),
            metadata=metadata,
        )

    async def _publish(
        self,
        event_type: EventType,
        game: Game,
        details: dict,
    ) -> None:
        event = self._create_event(event_type, game, details)
        await self._transport.publish(event)

    async def on_game_started(self, game: Game, details: GameStartedDetails) -> None:
        await self._publish(EventType.GAME_STARTED, game, details.to_dict())

    async def on_game_completed(self, game: Game, details: GameCompletedDetails) -> None:
        await self._publish(EventType.GAME_COMPLETED, game, details.to_dict())

    async def on_hand_started(self, game: Game, details: HandStartedDetails) -> None:
        await self._publish(EventType.HAND_STARTED, game, details.to_dict())

    async def on_hand_completed(self, game: Game, details: HandOutcomeDetails) -> None:
        await self._publish(EventType.HAND_COMPLETED, game, details.to_dict())

    async def on_round_started(self, game: Game, details: RoundStartedDetails) -> None:
        await self._publish(EventType.ROUND_STARTED, game, details.to_dict())

    async def on_round_completed(self, game: Game, details: RoundCompletedDetails) -> None:
        await self._publish(EventType.ROUND_COMPLETED, game, details.to_dict())

    async def on_blinds_posted(self, game: Game, details: BlindsPostedDetails) -> None:
        await self._publish(EventType.BLINDS_POSTED, game, details.to_dict())

    async def on_action_applied(self, game: Game, details: ActionAppliedDetails) -> None:
        await self._publish(EventType.ACTION_APPLIED, game, details.to_dict())

    async def on_hole_cards_dealt(self, game: Game, details: HoleCardsDealtDetails) -> None:
        await self._publish(EventType.HOLE_CARDS_DEALT, game, details.to_dict())

    async def on_player_to_act(self, game: Game, details: PlayerToActDetails) -> None:
        await self._publish(EventType.PLAYER_TO_ACT, game, details.to_dict())
