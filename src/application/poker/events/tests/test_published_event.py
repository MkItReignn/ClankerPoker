from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.application.poker.events import EventType, PublishedEvent, PublishedEventMetadata


class TestPublishedEventMetadata:
    def test_creates_metadata_with_all_fields(self) -> None:
        timestamp = datetime(2025, 1, 15, 10, 30, 45, tzinfo=timezone.utc)

        metadata = PublishedEventMetadata(
            game_id="game-123",
            hand_number=5,
            timestamp=timestamp,
            sequence=10,
        )

        assert metadata.game_id == "game-123"
        assert metadata.hand_number == 5
        assert metadata.timestamp == timestamp
        assert metadata.sequence == 10

    def test_converts_to_dict_with_iso_timestamp(self) -> None:
        timestamp = datetime(2025, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        metadata = PublishedEventMetadata(
            game_id="game-123",
            hand_number=5,
            timestamp=timestamp,
            sequence=10,
        )

        result = metadata.to_dict()

        assert result == {
            "game_id": "game-123",
            "hand_number": 5,
            "timestamp": "2025-01-15T10:30:45+00:00",
            "sequence": 10,
        }


class TestPublishedEvent:
    def test_creates_event_with_all_fields(self) -> None:
        metadata = PublishedEventMetadata(
            game_id="game-123",
            hand_number=1,
            timestamp=datetime.now(timezone.utc),
            sequence=1,
        )
        details = {"player_count": 3}
        game_state = {"current_phase": "pre_flop"}

        event = PublishedEvent(
            event_type=EventType.GAME_STARTED,
            details=details,
            game_state=game_state,
            metadata=metadata,
        )

        assert event.event_type == EventType.GAME_STARTED
        assert event.details == details
        assert event.game_state == game_state
        assert event.metadata == metadata

    def test_converts_to_dict_with_all_components(self) -> None:
        timestamp = datetime(2025, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        metadata = PublishedEventMetadata(
            game_id="game-123",
            hand_number=2,
            timestamp=timestamp,
            sequence=5,
        )
        details = {"action_type": "fold", "player_id": "player-1"}
        game_state = {"pot": 100, "phase": "flop"}

        event = PublishedEvent(
            event_type=EventType.ACTION_APPLIED,
            details=details,
            game_state=game_state,
            metadata=metadata,
        )

        result = event.to_dict()

        assert result == {
            "event_type": EventType.ACTION_APPLIED,
            "details": {"action_type": "fold", "player_id": "player-1"},
            "game_state": {"pot": 100, "phase": "flop"},
            "metadata": {
                "game_id": "game-123",
                "hand_number": 2,
                "timestamp": "2025-01-15T10:30:45+00:00",
                "sequence": 5,
            },
        }

    def test_handles_empty_details(self) -> None:
        metadata = PublishedEventMetadata(
            game_id="game-123",
            hand_number=1,
            timestamp=datetime.now(timezone.utc),
            sequence=1,
        )

        event = PublishedEvent(
            event_type=EventType.ROUND_STARTED,
            details={},
            game_state={"phase": "flop"},
            metadata=metadata,
        )

        result = event.to_dict()
        assert result["details"] == {}

    def test_handles_complex_nested_details(self) -> None:
        metadata = PublishedEventMetadata(
            game_id="game-456",
            hand_number=3,
            timestamp=datetime.now(timezone.utc),
            sequence=8,
        )
        details = {
            "players": [
                {"id": "p1", "chips": 100},
                {"id": "p2", "chips": 200},
            ],
            "blinds": {"small": 10, "big": 20},
        }

        event = PublishedEvent(
            event_type=EventType.HAND_STARTED,
            details=details,
            game_state={"phase": "pre_flop"},
            metadata=metadata,
        )

        result = event.to_dict()
        assert result["details"]["players"] == details["players"]
        assert result["details"]["blinds"] == details["blinds"]
