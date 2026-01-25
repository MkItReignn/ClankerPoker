from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.application.poker.events import EventType, PublishedEvent, PublishedEventMetadata
from src.infrastructure.realtime.mock_transport import InMemoryTransport, MockTransport


class TestInMemoryTransport:
    @pytest.mark.asyncio
    async def test_stores_published_event(self) -> None:
        transport = InMemoryTransport()
        event = PublishedEvent(
            event_type=EventType.GAME_STARTED,
            details={"player_count": 3},
            game_state={"phase": "pre_flop"},
            metadata=PublishedEventMetadata(
                game_id="game-1",
                hand_number=1,
                timestamp=datetime.now(timezone.utc),
                sequence=1,
            ),
        )

        await transport.publish(event)

        assert transport.event_count == 1
        assert transport.get_last_event() == event

    @pytest.mark.asyncio
    async def test_returns_copy_of_events_list(self) -> None:
        transport = InMemoryTransport()
        event = PublishedEvent(
            event_type=EventType.GAME_STARTED,
            details={},
            game_state={},
            metadata=PublishedEventMetadata(
                game_id="game-1",
                hand_number=1,
                timestamp=datetime.now(timezone.utc),
                sequence=1,
            ),
        )
        await transport.publish(event)

        events_copy = transport.events
        events_copy.append(event)

        assert transport.event_count == 1

    @pytest.mark.asyncio
    async def test_stores_multiple_events_in_order(self) -> None:
        transport = InMemoryTransport()
        event1 = PublishedEvent(
            event_type=EventType.GAME_STARTED,
            details={},
            game_state={},
            metadata=PublishedEventMetadata(
                game_id="game-1", hand_number=1, timestamp=datetime.now(timezone.utc), sequence=1
            ),
        )
        event2 = PublishedEvent(
            event_type=EventType.HAND_STARTED,
            details={},
            game_state={},
            metadata=PublishedEventMetadata(
                game_id="game-1", hand_number=1, timestamp=datetime.now(timezone.utc), sequence=2
            ),
        )

        await transport.publish(event1)
        await transport.publish(event2)

        assert transport.event_count == 2
        assert transport.events[0] == event1
        assert transport.events[1] == event2
        assert transport.get_last_event() == event2

    @pytest.mark.asyncio
    async def test_filters_events_by_type(self) -> None:
        transport = InMemoryTransport()
        event1 = PublishedEvent(
            event_type=EventType.GAME_STARTED,
            details={},
            game_state={},
            metadata=PublishedEventMetadata(
                game_id="game-1", hand_number=1, timestamp=datetime.now(timezone.utc), sequence=1
            ),
        )
        event2 = PublishedEvent(
            event_type=EventType.ACTION_APPLIED,
            details={},
            game_state={},
            metadata=PublishedEventMetadata(
                game_id="game-1", hand_number=1, timestamp=datetime.now(timezone.utc), sequence=2
            ),
        )
        event3 = PublishedEvent(
            event_type=EventType.ACTION_APPLIED,
            details={},
            game_state={},
            metadata=PublishedEventMetadata(
                game_id="game-1", hand_number=1, timestamp=datetime.now(timezone.utc), sequence=3
            ),
        )

        await transport.publish(event1)
        await transport.publish(event2)
        await transport.publish(event3)

        action_events = transport.get_events_by_type(EventType.ACTION_APPLIED)

        assert len(action_events) == 2
        assert action_events[0] == event2
        assert action_events[1] == event3

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_matching_type(self) -> None:
        transport = InMemoryTransport()
        event = PublishedEvent(
            event_type=EventType.GAME_STARTED,
            details={},
            game_state={},
            metadata=PublishedEventMetadata(
                game_id="game-1", hand_number=1, timestamp=datetime.now(timezone.utc), sequence=1
            ),
        )
        await transport.publish(event)

        result = transport.get_events_by_type(EventType.GAME_COMPLETED)

        assert result == []

    @pytest.mark.asyncio
    async def test_clears_all_events(self) -> None:
        transport = InMemoryTransport()
        event1 = PublishedEvent(
            event_type=EventType.GAME_STARTED,
            details={},
            game_state={},
            metadata=PublishedEventMetadata(
                game_id="game-1", hand_number=1, timestamp=datetime.now(timezone.utc), sequence=1
            ),
        )
        event2 = PublishedEvent(
            event_type=EventType.HAND_STARTED,
            details={},
            game_state={},
            metadata=PublishedEventMetadata(
                game_id="game-1", hand_number=1, timestamp=datetime.now(timezone.utc), sequence=2
            ),
        )
        await transport.publish(event1)
        await transport.publish(event2)

        transport.clear()

        assert transport.event_count == 0
        assert transport.events == []
        assert transport.get_last_event() is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_last_event(self) -> None:
        transport = InMemoryTransport()

        result = transport.get_last_event()

        assert result is None

    @pytest.mark.asyncio
    async def test_publish_batch_extends_events(self) -> None:
        transport = InMemoryTransport()
        event1 = PublishedEvent(
            event_type=EventType.GAME_STARTED,
            details={},
            game_state={},
            metadata=PublishedEventMetadata(
                game_id="game-1", hand_number=1, timestamp=datetime.now(timezone.utc), sequence=1
            ),
        )
        event2 = PublishedEvent(
            event_type=EventType.HAND_STARTED,
            details={},
            game_state={},
            metadata=PublishedEventMetadata(
                game_id="game-1", hand_number=1, timestamp=datetime.now(timezone.utc), sequence=2
            ),
        )

        await transport.publish_batch([event1, event2])

        assert transport.event_count == 2
        assert transport.events[0] == event1
        assert transport.events[1] == event2


class TestMockTransport:
    @pytest.mark.asyncio
    async def test_stores_events_when_store_events_is_true(self) -> None:
        transport = MockTransport(store_events=True)
        event = PublishedEvent(
            event_type=EventType.GAME_STARTED,
            details={"player_count": 3},
            game_state={},
            metadata=PublishedEventMetadata(
                game_id="game-1",
                hand_number=1,
                timestamp=datetime.now(timezone.utc),
                sequence=1,
            ),
        )

        await transport.publish(event)

        assert len(transport.events) == 1
        assert transport.events[0] == event

    @pytest.mark.asyncio
    async def test_does_not_store_events_when_store_events_is_false(self) -> None:
        transport = MockTransport(store_events=False)
        event = PublishedEvent(
            event_type=EventType.GAME_STARTED,
            details={},
            game_state={},
            metadata=PublishedEventMetadata(
                game_id="game-1",
                hand_number=1,
                timestamp=datetime.now(timezone.utc),
                sequence=1,
            ),
        )

        await transport.publish(event)

        assert len(transport.events) == 0

    @pytest.mark.asyncio
    async def test_writes_event_to_file_when_output_file_specified(self, tmp_path: Path) -> None:
        output_file = tmp_path / "events.jsonl"
        transport = MockTransport(output_file=output_file, store_events=True)
        timestamp = datetime(2025, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        event = PublishedEvent(
            event_type=EventType.GAME_STARTED,
            details={"player_count": 3},
            game_state={"phase": "pre_flop"},
            metadata=PublishedEventMetadata(
                game_id="game-1",
                hand_number=1,
                timestamp=timestamp,
                sequence=1,
            ),
        )

        await transport.publish(event)
        await transport.close()

        assert output_file.exists()
        content = output_file.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["event_type"] == EventType.GAME_STARTED
        assert parsed["details"]["player_count"] == 3

    @pytest.mark.asyncio
    async def test_writes_multiple_events_as_jsonl(self, tmp_path: Path) -> None:
        output_file = tmp_path / "events.jsonl"
        transport = MockTransport(output_file=output_file)
        event1 = PublishedEvent(
            event_type=EventType.GAME_STARTED,
            details={},
            game_state={},
            metadata=PublishedEventMetadata(
                game_id="game-1", hand_number=1, timestamp=datetime.now(timezone.utc), sequence=1
            ),
        )
        event2 = PublishedEvent(
            event_type=EventType.HAND_STARTED,
            details={},
            game_state={},
            metadata=PublishedEventMetadata(
                game_id="game-1", hand_number=1, timestamp=datetime.now(timezone.utc), sequence=2
            ),
        )

        await transport.publish(event1)
        await transport.publish(event2)
        await transport.close()

        content = output_file.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 2

    @pytest.mark.asyncio
    async def test_creates_parent_directories_for_output_file(self, tmp_path: Path) -> None:
        output_file = tmp_path / "nested" / "directory" / "events.jsonl"
        transport = MockTransport(output_file=output_file)
        event = PublishedEvent(
            event_type=EventType.GAME_STARTED,
            details={},
            game_state={},
            metadata=PublishedEventMetadata(
                game_id="game-1", hand_number=1, timestamp=datetime.now(timezone.utc), sequence=1
            ),
        )

        await transport.publish(event)
        await transport.close()

        assert output_file.exists()
        assert output_file.parent.exists()

    @pytest.mark.asyncio
    async def test_filters_events_by_type(self) -> None:
        transport = MockTransport(store_events=True)
        event1 = PublishedEvent(
            event_type=EventType.GAME_STARTED,
            details={},
            game_state={},
            metadata=PublishedEventMetadata(
                game_id="game-1", hand_number=1, timestamp=datetime.now(timezone.utc), sequence=1
            ),
        )
        event2 = PublishedEvent(
            event_type=EventType.ACTION_APPLIED,
            details={},
            game_state={},
            metadata=PublishedEventMetadata(
                game_id="game-1", hand_number=1, timestamp=datetime.now(timezone.utc), sequence=2
            ),
        )
        await transport.publish(event1)
        await transport.publish(event2)

        result = transport.get_events_by_type(EventType.ACTION_APPLIED)

        assert len(result) == 1
        assert result[0] == event2

    @pytest.mark.asyncio
    async def test_clears_stored_events(self) -> None:
        transport = MockTransport(store_events=True)
        event = PublishedEvent(
            event_type=EventType.GAME_STARTED,
            details={},
            game_state={},
            metadata=PublishedEventMetadata(
                game_id="game-1", hand_number=1, timestamp=datetime.now(timezone.utc), sequence=1
            ),
        )
        await transport.publish(event)

        transport.clear()

        assert len(transport.events) == 0

    @pytest.mark.asyncio
    async def test_context_manager_closes_file(self, tmp_path: Path) -> None:
        output_file = tmp_path / "events.jsonl"
        event = PublishedEvent(
            event_type=EventType.GAME_STARTED,
            details={},
            game_state={},
            metadata=PublishedEventMetadata(
                game_id="game-1", hand_number=1, timestamp=datetime.now(timezone.utc), sequence=1
            ),
        )

        async with MockTransport(output_file=output_file) as transport:
            await transport.publish(event)

        assert output_file.exists()
        content = output_file.read_text()
        assert len(content.strip().split("\n")) == 1

    @pytest.mark.asyncio
    async def test_publish_batch_publishes_all_events(self) -> None:
        transport = MockTransport(store_events=True)
        event1 = PublishedEvent(
            event_type=EventType.GAME_STARTED,
            details={},
            game_state={},
            metadata=PublishedEventMetadata(
                game_id="game-1", hand_number=1, timestamp=datetime.now(timezone.utc), sequence=1
            ),
        )
        event2 = PublishedEvent(
            event_type=EventType.HAND_STARTED,
            details={},
            game_state={},
            metadata=PublishedEventMetadata(
                game_id="game-1", hand_number=1, timestamp=datetime.now(timezone.utc), sequence=2
            ),
        )

        await transport.publish_batch([event1, event2])

        assert len(transport.events) == 2
        assert transport.events[0] == event1
        assert transport.events[1] == event2
