from collections.abc import Callable

import pytest

from src.application.poker.events import EventPublisher, EventType
from src.application.poker.state_observers.details import (
    ActionAppliedDetails,
    BlindInfo,
    BlindsPostedDetails,
    GameCompletedDetails,
    GameStartedDetails,
    HandOutcomeDetails,
    HandStartedDetails,
    HoleCardDealtDetail,
    HoleCardsDealtDetails,
    PlayerOutcome,
    RoundCompletedDetails,
    RoundStartedDetails,
    WinnerInfo,
)
from src.domain.models.actions import ActionType
from src.domain.models.card import Card, Rank, Suit
from src.domain.models.chips import ChipAmount
from src.domain.models.game import Game, GameStatus, HandPhase
from src.domain.models.hand import Hand
from src.domain.models.player import (
    BettingRoundActionStatus,
    HandParticipationStatus,
    PlayerId,
)
from src.domain.models.seat import Seat
from src.infrastructure.realtime.mock_transport import InMemoryTransport


class TestEventPublisherSequenceNumbers:
    @pytest.mark.asyncio
    async def test_increments_sequence_for_each_event(
        self, game_factory: Callable[..., Game], sample_player_factory
    ) -> None:
        transport = InMemoryTransport()
        publisher = EventPublisher(transport)
        players = [
            sample_player_factory(
                PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)
            ),
            sample_player_factory(
                PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)
            ),
        ]
        game = game_factory(players=players)

        details1 = GameStartedDetails(
            player_count=2, starting_chips=ChipAmount(1000)
        )
        details2 = HandStartedDetails(
            hand_number=1,
            button_seat=Seat.SEAT_0,
            sb_seat=Seat.SEAT_1,
            bb_seat=Seat.SEAT_0,
        )

        await publisher.on_game_started(game, details1)
        await publisher.on_hand_started(game, details2)

        assert transport.events[0].metadata.sequence == 1
        assert transport.events[1].metadata.sequence == 2

    @pytest.mark.asyncio
    async def test_maintains_sequence_across_different_event_types(
        self, game_factory: Callable[..., Game], sample_player_factory
    ) -> None:
        transport = InMemoryTransport()
        publisher = EventPublisher(transport)
        players = [
            sample_player_factory(
                PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)
            ),
            sample_player_factory(
                PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)
            ),
        ]
        game = game_factory(players=players)

        await publisher.on_game_started(
            game, GameStartedDetails(2, ChipAmount(1000))
        )
        await publisher.on_hand_started(
            game,
            HandStartedDetails(
                hand_number=1,
                button_seat=Seat.SEAT_0,
                sb_seat=Seat.SEAT_1,
                bb_seat=Seat.SEAT_0,
            ),
        )
        await publisher.on_round_started(
            game, RoundStartedDetails(phase=HandPhase.PRE_FLOP, new_cards=())
        )
        await publisher.on_round_completed(game, RoundCompletedDetails())

        sequences = [event.metadata.sequence for event in transport.events]
        assert sequences == [1, 2, 3, 4]


class TestEventPublisherGameEvents:
    @pytest.mark.asyncio
    async def test_publishes_game_started_with_correct_type_and_details(
        self, game_factory: Callable[..., Game], sample_player_factory
    ) -> None:
        transport = InMemoryTransport()
        publisher = EventPublisher(transport)
        players = [
            sample_player_factory(
                PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)
            ),
            sample_player_factory(
                PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)
            ),
        ]
        game = game_factory(players=players)
        details = GameStartedDetails(
            player_count=2, starting_chips=ChipAmount(1000)
        )

        await publisher.on_game_started(game, details)

        assert transport.event_count == 1
        event = transport.get_last_event()
        assert event is not None
        assert event.event_type == EventType.GAME_STARTED
        assert event.details["player_count"] == 2
        assert event.details["starting_chips"] == 1000

    @pytest.mark.asyncio
    async def test_publishes_game_completed_with_winner_info(
        self, game_factory: Callable[..., Game], sample_player_factory
    ) -> None:
        from src.domain.models.game import HandOutcome

        transport = InMemoryTransport()
        publisher = EventPublisher(transport)
        players = [
            sample_player_factory(
                PlayerId("p1"),
                Seat.SEAT_0,
                ChipAmount(2000),
                table_finish_position=1,
            ),
            sample_player_factory(
                PlayerId("p2"),
                Seat.SEAT_1,
                ChipAmount(0),
                table_finish_position=2,
            ),
        ]
        outcome = HandOutcome(
            hand_number=5, winners=[(PlayerId("p1"), ChipAmount(2000))]
        )
        game = game_factory(
            players=players,
            status=GameStatus.COMPLETED,
            hand_number=5,
            outcome=outcome,
        )
        details = GameCompletedDetails(
            winner_id="p1",
            winner_name="Player p1",
            total_hands=5,
            final_standings=(),
        )

        await publisher.on_game_completed(game, details)

        assert transport.event_count == 1
        event = transport.get_last_event()
        assert event is not None
        assert event.event_type == EventType.GAME_COMPLETED
        assert event.details["winner_id"] == "p1"
        assert event.details["total_hands"] == 5


class TestEventPublisherHandEvents:
    @pytest.mark.asyncio
    async def test_publishes_hand_started_with_blind_positions(
        self, game_factory: Callable[..., Game], sample_player_factory
    ) -> None:
        transport = InMemoryTransport()
        publisher = EventPublisher(transport)
        players = [
            sample_player_factory(
                PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)
            ),
            sample_player_factory(
                PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)
            ),
        ]
        game = game_factory(players=players, hand_number=3)
        details = HandStartedDetails(
            hand_number=3,
            button_seat=Seat.SEAT_0,
            sb_seat=Seat.SEAT_1,
            bb_seat=Seat.SEAT_0,
        )

        await publisher.on_hand_started(game, details)

        event = transport.get_last_event()
        assert event is not None
        assert event.event_type == EventType.HAND_STARTED
        assert event.details["hand_number"] == 3
        assert event.details["button_seat"] == 0
        assert event.details["sb_seat"] == 1
        assert event.details["bb_seat"] == 0

    @pytest.mark.asyncio
    async def test_publishes_hand_completed_with_outcome(
        self, game_factory: Callable[..., Game], sample_player_factory
    ) -> None:
        transport = InMemoryTransport()
        publisher = EventPublisher(transport)
        players = [
            sample_player_factory(
                PlayerId("p1"), Seat.SEAT_0, ChipAmount(1500)
            ),
            sample_player_factory(
                PlayerId("p2"), Seat.SEAT_1, ChipAmount(500)
            ),
        ]
        game = game_factory(players=players)
        details = HandOutcomeDetails(
            winners=(
                WinnerInfo(
                    player_id="p1",
                    player_name="Player p1",
                    amount=ChipAmount(100),
                ),
            ),
            eliminated=(),
            showdown=None,
            pot_amount=ChipAmount(100),
            player_outcomes=(
                PlayerOutcome(
                    player_id="p1",
                    player_name="Player p1",
                    chips_won=ChipAmount(100),
                    final_stack=ChipAmount(1500),
                ),
            ),
        )

        await publisher.on_hand_completed(game, details)

        event = transport.get_last_event()
        assert event is not None
        assert event.event_type == EventType.HAND_COMPLETED
        assert len(event.details["winners"]) == 1
        assert event.details["pot_amount"] == 100

    @pytest.mark.asyncio
    async def test_publishes_hole_cards_dealt(
        self,
        game_factory: Callable[..., Game],
        sample_player_factory,
        sample_hand,
    ) -> None:
        transport = InMemoryTransport()
        publisher = EventPublisher(transport)
        players = [
            sample_player_factory(
                PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)
            ),
            sample_player_factory(
                PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)
            ),
        ]
        game = game_factory(players=players)
        details = HoleCardsDealtDetails(
            players={
                "p1": HoleCardDealtDetail(
                    player_id="p1",
                    player_name="Player p1",
                    cards=sample_hand,
                    deal_order=0,
                )
            }
        )

        await publisher.on_hole_cards_dealt(game, details)

        event = transport.get_last_event()
        assert event is not None
        assert event.event_type == EventType.HOLE_CARDS_DEALT
        assert "p1" in event.details


class TestEventPublisherRoundEvents:
    @pytest.mark.asyncio
    async def test_publishes_round_started_for_pre_flop(
        self, game_factory: Callable[..., Game], sample_player_factory
    ) -> None:
        transport = InMemoryTransport()
        publisher = EventPublisher(transport)
        players = [
            sample_player_factory(
                PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)
            ),
            sample_player_factory(
                PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)
            ),
        ]
        game = game_factory(
            players=players,
            current_phase=HandPhase.PRE_FLOP,
            position_to_act=-1,
        )
        details = RoundStartedDetails(phase=HandPhase.PRE_FLOP, new_cards=())

        await publisher.on_round_started(game, details)

        events = transport.events
        assert len(events) == 1
        assert events[0].event_type == EventType.ROUND_STARTED
        assert events[0].details["phase"] == HandPhase.PRE_FLOP.value

    @pytest.mark.asyncio
    async def test_publishes_round_started_and_player_to_act_for_flop(
        self, game_factory: Callable[..., Game], sample_player_factory
    ) -> None:
        transport = InMemoryTransport()
        publisher = EventPublisher(transport)
        players = [
            sample_player_factory(
                PlayerId("p1"),
                Seat.SEAT_0,
                ChipAmount(1000),
                betting_status=BettingRoundActionStatus.NEEDS_ACTION,
            ),
            sample_player_factory(
                PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)
            ),
        ]
        game = game_factory(
            players=players, current_phase=HandPhase.FLOP, position_to_act=0
        )
        flop_cards = (
            Card(rank=Rank.ACE, suit=Suit.SPADES),
            Card(rank=Rank.KING, suit=Suit.HEARTS),
            Card(rank=Rank.QUEEN, suit=Suit.DIAMONDS),
        )
        details = RoundStartedDetails(
            phase=HandPhase.FLOP, new_cards=flop_cards
        )

        await publisher.on_round_started(game, details)

        events = transport.events
        assert len(events) == 2
        assert events[0].event_type == EventType.ROUND_STARTED
        assert events[1].event_type == EventType.PLAYER_TO_ACT

    @pytest.mark.asyncio
    async def test_publishes_round_started_without_player_to_act_when_no_player_to_act(
        self, game_factory: Callable[..., Game], sample_player_factory
    ) -> None:
        transport = InMemoryTransport()
        publisher = EventPublisher(transport)
        players = [
            sample_player_factory(
                PlayerId("p1"),
                Seat.SEAT_0,
                ChipAmount(1000),
                betting_status=BettingRoundActionStatus.ACTED,
            ),
            sample_player_factory(
                PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)
            ),
        ]
        game = game_factory(
            players=players, current_phase=HandPhase.TURN, position_to_act=-1
        )
        details = RoundStartedDetails(
            phase=HandPhase.TURN,
            new_cards=(Card(rank=Rank.TEN, suit=Suit.CLUBS),),
        )

        await publisher.on_round_started(game, details)

        events = transport.events
        assert len(events) == 1
        assert events[0].event_type == EventType.ROUND_STARTED

    @pytest.mark.asyncio
    async def test_publishes_round_completed(
        self, game_factory: Callable[..., Game], sample_player_factory
    ) -> None:
        transport = InMemoryTransport()
        publisher = EventPublisher(transport)
        players = [
            sample_player_factory(
                PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)
            ),
            sample_player_factory(
                PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)
            ),
        ]
        game = game_factory(players=players)
        details = RoundCompletedDetails()

        await publisher.on_round_completed(game, details)

        event = transport.get_last_event()
        assert event is not None
        assert event.event_type == EventType.ROUND_COMPLETED
        assert event.details == {}


class TestEventPublisherBettingEvents:
    @pytest.mark.asyncio
    async def test_publishes_blinds_posted_with_both_blinds(
        self, game_factory: Callable[..., Game], sample_player_factory
    ) -> None:
        transport = InMemoryTransport()
        publisher = EventPublisher(transport)
        players = [
            sample_player_factory(
                PlayerId("p1"),
                Seat.SEAT_0,
                ChipAmount(1000),
                betting_status=BettingRoundActionStatus.NEEDS_ACTION,
            ),
            sample_player_factory(
                PlayerId("p2"),
                Seat.SEAT_1,
                ChipAmount(1000),
                betting_status=BettingRoundActionStatus.NEEDS_ACTION,
            ),
        ]
        game = game_factory(players=players, position_to_act=0)
        details = BlindsPostedDetails(
            small_blind=BlindInfo(
                player_id="p1", player_name="Player p1", amount=ChipAmount(10)
            ),
            big_blind=BlindInfo(
                player_id="p2", player_name="Player p2", amount=ChipAmount(20)
            ),
        )

        await publisher.on_blinds_posted(game, details)

        events = transport.events
        assert len(events) == 2
        assert events[0].event_type == EventType.BLINDS_POSTED
        assert events[0].details["small_blind"]["player_id"] == "p1"
        assert events[0].details["big_blind"]["player_id"] == "p2"
        assert events[1].event_type == EventType.PLAYER_TO_ACT

    @pytest.mark.asyncio
    async def test_publishes_blinds_posted_without_player_to_act_when_none(
        self, game_factory: Callable[..., Game], sample_player_factory
    ) -> None:
        transport = InMemoryTransport()
        publisher = EventPublisher(transport)
        players = [
            sample_player_factory(
                PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)
            ),
            sample_player_factory(
                PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)
            ),
        ]
        game = game_factory(players=players, position_to_act=-1)
        details = BlindsPostedDetails(
            small_blind=BlindInfo(
                player_id="p1", player_name="Player p1", amount=ChipAmount(10)
            ),
            big_blind=BlindInfo(
                player_id="p2", player_name="Player p2", amount=ChipAmount(20)
            ),
        )

        await publisher.on_blinds_posted(game, details)

        events = transport.events
        assert len(events) == 1
        assert events[0].event_type == EventType.BLINDS_POSTED

    @pytest.mark.asyncio
    async def test_publishes_action_applied_with_player_details(
        self, game_factory: Callable[..., Game], sample_player_factory
    ) -> None:
        transport = InMemoryTransport()
        publisher = EventPublisher(transport)
        players = [
            sample_player_factory(
                PlayerId("p1"),
                Seat.SEAT_0,
                ChipAmount(1000),
                betting_status=BettingRoundActionStatus.NEEDS_ACTION,
            ),
            sample_player_factory(
                PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)
            ),
        ]
        game = game_factory(players=players, position_to_act=0)
        details = ActionAppliedDetails(
            player_id="p1",
            player_name="Player p1",
            action_type=ActionType.RAISE,
            amount=ChipAmount(50),
            narration=None,
        )

        await publisher.on_action_applied(game, details)

        events = transport.events
        assert len(events) == 2
        assert events[0].event_type == EventType.ACTION_APPLIED
        assert events[0].details["player_id"] == "p1"
        assert events[0].details["action_type"] == "raise"
        assert events[0].details["amount"] == 50
        assert events[1].event_type == EventType.PLAYER_TO_ACT

    @pytest.mark.asyncio
    async def test_publishes_action_applied_without_amount_for_fold(
        self, game_factory: Callable[..., Game], sample_player_factory
    ) -> None:
        transport = InMemoryTransport()
        publisher = EventPublisher(transport)
        players = [
            sample_player_factory(
                PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)
            ),
            sample_player_factory(
                PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)
            ),
        ]
        game = game_factory(players=players, position_to_act=-1)
        details = ActionAppliedDetails(
            player_id="p1",
            player_name="Player p1",
            action_type=ActionType.FOLD,
            amount=None,
            narration=None,
        )

        await publisher.on_action_applied(game, details)

        events = transport.events
        assert events[0].details["action_type"] == "fold"
        assert events[0].details["amount"] is None


class TestEventPublisherMetadata:
    @pytest.mark.asyncio
    async def test_includes_game_id_in_metadata(
        self, game_factory: Callable[..., Game], sample_player_factory
    ) -> None:
        transport = InMemoryTransport()
        publisher = EventPublisher(transport)
        players = [
            sample_player_factory(
                PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)
            ),
            sample_player_factory(
                PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)
            ),
        ]
        game = game_factory(players=players)
        details = GameStartedDetails(
            player_count=2, starting_chips=ChipAmount(1000)
        )

        await publisher.on_game_started(game, details)

        event = transport.get_last_event()
        assert event is not None
        assert event.metadata.game_id == "test-game"

    @pytest.mark.asyncio
    async def test_includes_hand_number_in_metadata(
        self, game_factory: Callable[..., Game], sample_player_factory
    ) -> None:
        transport = InMemoryTransport()
        publisher = EventPublisher(transport)
        players = [
            sample_player_factory(
                PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)
            ),
            sample_player_factory(
                PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)
            ),
        ]
        game = game_factory(players=players, hand_number=7)
        details = GameStartedDetails(
            player_count=2, starting_chips=ChipAmount(1000)
        )

        await publisher.on_game_started(game, details)

        event = transport.get_last_event()
        assert event is not None
        assert event.metadata.hand_number == 7

    @pytest.mark.asyncio
    async def test_includes_timestamp_in_metadata(
        self, game_factory: Callable[..., Game], sample_player_factory
    ) -> None:
        transport = InMemoryTransport()
        publisher = EventPublisher(transport)
        players = [
            sample_player_factory(
                PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)
            ),
            sample_player_factory(
                PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)
            ),
        ]
        game = game_factory(players=players)
        details = GameStartedDetails(
            player_count=2, starting_chips=ChipAmount(1000)
        )

        await publisher.on_game_started(game, details)

        event = transport.get_last_event()
        assert event is not None
        assert event.metadata.timestamp is not None


class TestEventPublisherGameState:
    @pytest.mark.asyncio
    async def test_includes_game_state_snapshot(
        self, game_factory: Callable[..., Game], sample_player_factory
    ) -> None:
        transport = InMemoryTransport()
        publisher = EventPublisher(transport)
        players = [
            sample_player_factory(
                PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)
            ),
            sample_player_factory(
                PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)
            ),
        ]
        game = game_factory(players=players, current_phase=HandPhase.FLOP)
        details = GameStartedDetails(
            player_count=2, starting_chips=ChipAmount(1000)
        )

        await publisher.on_game_started(game, details)

        event = transport.get_last_event()
        assert event is not None
        assert event.game_state is not None
        assert "hand_state" in event.game_state
        assert event.game_state["hand_state"]["current_phase"] == "flop"

    @pytest.mark.asyncio
    async def test_game_state_contains_player_information(
        self, game_factory: Callable[..., Game], sample_player_factory
    ) -> None:
        transport = InMemoryTransport()
        publisher = EventPublisher(transport)
        players = [
            sample_player_factory(
                PlayerId("p1"), Seat.SEAT_0, ChipAmount(1500), name="Alice"
            ),
            sample_player_factory(
                PlayerId("p2"), Seat.SEAT_1, ChipAmount(500), name="Bob"
            ),
        ]
        game = game_factory(players=players)
        details = GameStartedDetails(
            player_count=2, starting_chips=ChipAmount(1000)
        )

        await publisher.on_game_started(game, details)

        event = transport.get_last_event()
        assert event is not None
        assert "players" in event.game_state
        assert len(event.game_state["players"]) == 2


class TestEventPublisherEdgeCases:
    @pytest.mark.asyncio
    async def test_handles_multiple_sequential_events(
        self, game_factory: Callable[..., Game], sample_player_factory
    ) -> None:
        transport = InMemoryTransport()
        publisher = EventPublisher(transport)
        players = [
            sample_player_factory(
                PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)
            ),
            sample_player_factory(
                PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)
            ),
        ]
        game = game_factory(players=players)

        await publisher.on_game_started(
            game, GameStartedDetails(2, ChipAmount(1000))
        )
        await publisher.on_hand_started(
            game,
            HandStartedDetails(1, Seat.SEAT_0, Seat.SEAT_1, Seat.SEAT_0),
        )
        await publisher.on_round_started(
            game, RoundStartedDetails(HandPhase.PRE_FLOP, ())
        )

        assert transport.event_count == 3
        assert all(
            event.metadata.game_id == "test-game" for event in transport.events
        )

    @pytest.mark.asyncio
    async def test_does_not_publish_player_to_act_when_player_id_is_none(
        self, game_factory: Callable[..., Game], sample_player_factory
    ) -> None:
        transport = InMemoryTransport()
        publisher = EventPublisher(transport)
        players = [
            sample_player_factory(
                PlayerId("p1"),
                Seat.SEAT_0,
                ChipAmount(1000),
                participation_status=HandParticipationStatus.FOLDED,
            ),
            sample_player_factory(
                PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)
            ),
        ]
        game = game_factory(players=players, position_to_act=-1)
        details = ActionAppliedDetails(
            player_id="p1",
            player_name="Player p1",
            action_type=ActionType.FOLD,
            amount=None,
            narration=None,
        )

        await publisher.on_action_applied(game, details)

        assert transport.event_count == 1
        assert transport.events[0].event_type == EventType.ACTION_APPLIED

    @pytest.mark.asyncio
    async def test_publishes_player_to_act_for_turn_round(
        self, game_factory: Callable[..., Game], sample_player_factory
    ) -> None:
        transport = InMemoryTransport()
        publisher = EventPublisher(transport)
        players = [
            sample_player_factory(
                PlayerId("p1"),
                Seat.SEAT_0,
                ChipAmount(1000),
                betting_status=BettingRoundActionStatus.NEEDS_ACTION,
            ),
            sample_player_factory(
                PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)
            ),
        ]
        game = game_factory(
            players=players, current_phase=HandPhase.TURN, position_to_act=0
        )
        details = RoundStartedDetails(
            phase=HandPhase.TURN,
            new_cards=(Card(rank=Rank.TEN, suit=Suit.CLUBS),),
        )

        await publisher.on_round_started(game, details)

        assert len(transport.events) == 2
        assert transport.events[0].event_type == EventType.ROUND_STARTED
        assert transport.events[1].event_type == EventType.PLAYER_TO_ACT

    @pytest.mark.asyncio
    async def test_publishes_player_to_act_for_river_round(
        self, game_factory: Callable[..., Game], sample_player_factory
    ) -> None:
        transport = InMemoryTransport()
        publisher = EventPublisher(transport)
        players = [
            sample_player_factory(
                PlayerId("p1"),
                Seat.SEAT_0,
                ChipAmount(1000),
                betting_status=BettingRoundActionStatus.NEEDS_ACTION,
            ),
            sample_player_factory(
                PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)
            ),
        ]
        game = game_factory(
            players=players, current_phase=HandPhase.RIVER, position_to_act=0
        )
        details = RoundStartedDetails(
            phase=HandPhase.RIVER,
            new_cards=(Card(rank=Rank.TWO, suit=Suit.DIAMONDS),),
        )

        await publisher.on_round_started(game, details)

        assert len(transport.events) == 2
        assert transport.events[1].event_type == EventType.PLAYER_TO_ACT
