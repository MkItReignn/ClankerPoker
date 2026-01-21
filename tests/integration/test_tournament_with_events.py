"""Integration test for running a tournament with event persistence.

This test verifies that:
1. A tournament can run with a mocked action provider (BotActionProvider)
2. Events are published and persisted to a JSONL file
3. Game record is captured
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.application.poker.events.publisher import FrontEndEventPublisher
from src.application.poker.orchestration.poker_orchestrator import PokerOrchestrator
from src.application.poker.providers.bot_action_provider import BotActionProvider
from src.application.poker.orchestration.state_manager import PokerStateManager
from src.config.blind_schedule.config import BlindSchedule, BlindScheduleEntry
from src.config.poker.config import PokerGameConfig, PokerPlayerConfig
from src.config.tournament.config import PayoutStructure, TournamentConfig
from src.domain.models.blinds import BlindLevel
from src.domain.models.chips import ChipAmount
from src.domain.models.game import GameStatus
from src.domain.models.llm_model import LlmModel
from src.domain.utils import generate_game_id
from src.infrastructure.realtime.mock_transport import MockTransport


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """Create a data directory for test output."""
    data_path = tmp_path / "data"
    data_path.mkdir(parents=True, exist_ok=True)
    return data_path


@pytest.fixture
def two_player_configs() -> dict[str, PokerPlayerConfig]:
    """Create 2-player configurations for the test."""
    return {
        "player-1": PokerPlayerConfig(
            player_id="player-1",
            name="Bot Alice",
            model_id=LlmModel.OPENAI_GPT4O_MINI,
        ),
        "player-2": PokerPlayerConfig(
            player_id="player-2",
            name="Bot Bob",
            model_id=LlmModel.OPENAI_GPT4O_MINI,
        ),
    }


@pytest.fixture
def three_player_configs() -> dict[str, PokerPlayerConfig]:
    """Create 3-player configurations for the test."""
    return {
        "player-1": PokerPlayerConfig(
            player_id="player-1",
            name="Bot Alice",
            model_id=LlmModel.OPENAI_GPT4O_MINI,
        ),
        "player-2": PokerPlayerConfig(
            player_id="player-2",
            name="Bot Bob",
            model_id=LlmModel.OPENAI_GPT4O_MINI,
        ),
        "player-3": PokerPlayerConfig(
            player_id="player-3",
            name="Bot Charlie",
            model_id=LlmModel.OPENAI_GPT4O_MINI,
        ),
    }


@pytest.fixture
def poker_config(two_player_configs: dict[str, PokerPlayerConfig]) -> PokerGameConfig:
    """Create poker game configuration for 2 players."""
    return PokerGameConfig(player_configs=two_player_configs)


@pytest.fixture
def three_player_poker_config(three_player_configs: dict[str, PokerPlayerConfig]) -> PokerGameConfig:
    """Create poker game configuration for 3 players."""
    return PokerGameConfig(player_configs=three_player_configs)


def create_tournament_config(
    starting_chips: int = 200,
    small_blind: int = 10,
    big_blind: int = 20,
) -> TournamentConfig:
    """Create a tournament config for tests."""
    return TournamentConfig(
        buy_in_amount=ChipAmount(starting_chips),
        starting_chip_stack=ChipAmount(starting_chips),
        payout_structure=PayoutStructure.WINNER_TAKES_ALL,
        blind_schedule=BlindSchedule(
            entries=(
                BlindScheduleEntry(
                    level=BlindLevel(
                        small_blind=ChipAmount(small_blind),
                        big_blind=ChipAmount(big_blind),
                        level=1,
                    ),
                    start_hand=1,
                    duration_hands=100,
                ),
            )
        ),
    )


class TestTournamentWithEventPersistence:
    """Tests for running tournaments with event persistence."""

    @pytest.mark.asyncio
    async def test_tournament_runs_with_bot_provider_and_persists_events(
        self,
        data_dir: Path,
        three_player_poker_config: PokerGameConfig,
    ) -> None:
        """Run a complete tournament with mocked LLM and verify events are persisted."""
        # Arrange: Create tournament config
        tournament_config = create_tournament_config(
            starting_chips=500,
            small_blind=10,
            big_blind=20,
        )

        # Generate game_id first
        game_id = generate_game_id()

        # Create runner with all configuration
        state = PokerStateManager(
            config=three_player_poker_config,
            tournament_config=tournament_config,
            game_id=game_id,
            seed=12345,
        )

        # We need to initialize to get the game_id
        state.initialize()

        # Create transport that writes to JSONL file
        events_file = data_dir / f"events_{game_id}.jsonl"
        transport = MockTransport(output_file=events_file, store_events=True)

        # Create event publisher with transport
        event_publisher = FrontEndEventPublisher(
            transport=transport,
            game_id=game_id,
            buffer_events=True,
        )

        # Create a fresh runner for the actual orchestrator (since we already used the first one)
        state2 = PokerStateManager(
            config=three_player_poker_config,
            tournament_config=tournament_config,
            game_id=game_id,
            seed=12345,
        )
        action_provider = BotActionProvider.with_seed(42)

        orchestrator = PokerOrchestrator(
            state=state2,
            action_provider=action_provider,
            event_publisher=event_publisher,
            max_hands=50,
        )

        # Act: Run the tournament (runner creates game internally)
        result = await orchestrator.run_game()

        # Close transport to flush file
        await transport.close()

        # Assert: Tournament completed with a winner
        assert result.winner_id is not None
        assert result.winner_name is not None
        assert result.final_state.status == GameStatus.COMPLETED
        assert result.total_hands > 0
        assert result.total_actions > 0

        # Assert: Events were stored in memory
        assert len(transport.events) > 0

        # Assert: Events were written to file
        assert events_file.exists()

        # Read and verify JSONL file
        events_from_file = []
        with events_file.open("r") as f:
            for line in f:
                if line.strip():
                    events_from_file.append(json.loads(line))

        assert len(events_from_file) > 0
        assert len(events_from_file) == len(transport.events)

        # Verify event types present
        event_types = {e["event_type"] for e in events_from_file}
        assert "game_started" in event_types
        assert "hand_started" in event_types
        assert "action_taken" in event_types
        assert "game_ended" in event_types

        # Verify game_id is consistent across events
        result_game_id = result.final_state.id
        for event in events_from_file:
            assert event["game_id"] == result_game_id

        # Print summary for visibility
        print(f"\n=== Tournament Summary ===")
        print(f"Game ID: {result_game_id}")
        print(f"Winner: {result.winner_name} ({result.winner_id})")
        print(f"Total Hands: {result.total_hands}")
        print(f"Total Actions: {result.total_actions}")
        print(f"Events Persisted: {len(events_from_file)}")
        print(f"Event Types: {sorted(event_types)}")
        print(f"Events File: {events_file}")

    @pytest.mark.asyncio
    async def test_events_contain_expected_data(
        self,
        data_dir: Path,
        poker_config: PokerGameConfig,
    ) -> None:
        """Verify that persisted events contain the expected data structures."""
        # Arrange
        tournament_config = create_tournament_config(
            starting_chips=200,
            small_blind=10,
            big_blind=20,
        )

        # Generate game_id first
        game_id = generate_game_id()

        state = PokerStateManager(
            config=poker_config,
            tournament_config=tournament_config,
            game_id=game_id,
            seed=99999,
        )

        # Initialize for event file
        state.initialize()
        events_file = data_dir / f"events_{game_id}.jsonl"
        transport = MockTransport(output_file=events_file, store_events=True)

        event_publisher = FrontEndEventPublisher(
            transport=transport,
            game_id=game_id,
            buffer_events=True,
        )

        # Create fresh runner for orchestrator
        state2 = PokerStateManager(
            config=poker_config,
            tournament_config=tournament_config,
            game_id=game_id,
            seed=99999,
        )
        action_provider = BotActionProvider.with_seed(123)

        orchestrator = PokerOrchestrator(
            state=state2,
            action_provider=action_provider,
            event_publisher=event_publisher,
            max_hands=20,
        )

        # Act
        result = await orchestrator.run_game()
        await transport.close()

        # Assert: Read events
        events_from_file = []
        with events_file.open("r") as f:
            for line in f:
                if line.strip():
                    events_from_file.append(json.loads(line))

        # Verify game_started event structure
        game_started_events = [e for e in events_from_file if e["event_type"] == "game_started"]
        assert len(game_started_events) == 1
        game_started = game_started_events[0]
        assert "payload" in game_started
        assert "player_count" in game_started["payload"]
        assert "starting_chips" in game_started["payload"]
        assert game_started["payload"]["player_count"] == 2
        assert game_started["payload"]["starting_chips"] == 200

        # Verify hand_started events
        hand_started_events = [e for e in events_from_file if e["event_type"] == "hand_started"]
        assert len(hand_started_events) >= 1
        hand_started = hand_started_events[0]
        assert "player_states" in hand_started["payload"]
        assert len(hand_started["payload"]["player_states"]) == 2

        # Verify action_taken events
        action_events = [e for e in events_from_file if e["event_type"] == "action_taken"]
        assert len(action_events) > 0
        for action_event in action_events:
            payload = action_event["payload"]
            assert "player_id" in payload
            assert "action_type" in payload
            assert "chips_before" in payload
            assert "chips_after" in payload

        # Verify game_ended event
        game_ended_events = [e for e in events_from_file if e["event_type"] == "game_ended"]
        assert len(game_ended_events) == 1
        game_ended = game_ended_events[0]
        assert "winner_id" in game_ended["payload"]
        assert "total_hands" in game_ended["payload"]

        print(f"\n=== Event Data Verification ===")
        print(f"Total events: {len(events_from_file)}")
        print(f"Hand started events: {len(hand_started_events)}")
        print(f"Action events: {len(action_events)}")
        print(f"Winner: {game_ended['payload']['winner_name']}")

    @pytest.mark.asyncio
    async def test_record_is_captured(
        self,
        poker_config: PokerGameConfig,
    ) -> None:
        """Verify that game record is properly captured."""
        # Arrange
        tournament_config = create_tournament_config(
            starting_chips=200,
            small_blind=10,
            big_blind=20,
        )

        state = PokerStateManager(
            config=poker_config,
            tournament_config=tournament_config,
            game_id=generate_game_id(),
            seed=77777,
        )
        action_provider = BotActionProvider.with_seed(456)

        orchestrator = PokerOrchestrator(
            state=state,
            action_provider=action_provider,
            max_hands=15,
        )

        # Act
        result = await orchestrator.run_game()

        # Assert: Record is available
        assert result.record is not None
        assert result.record.game_id == result.final_state.id
        assert len(result.record.completed_hands) > 0

        # Verify completed hands have outcomes
        for hand in result.record.completed_hands:
            assert hand.outcome is not None
            assert len(hand.outcome.winner_ids) >= 1

        print(f"\n=== Record Verification ===")
        print(f"Game ID: {result.record.game_id}")
        print(f"Completed Hands: {len(result.record.completed_hands)}")
        print(f"Total Actions: {result.total_actions}")


class TestEventFileNaming:
    """Tests for event file naming convention."""

    @pytest.mark.asyncio
    async def test_events_written_to_correct_file_path(
        self,
        tmp_path: Path,
        poker_config: PokerGameConfig,
    ) -> None:
        """Verify events are written to data/events_{game_id}.jsonl."""
        # Arrange
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        tournament_config = create_tournament_config(
            starting_chips=100,
            small_blind=5,
            big_blind=10,
        )

        # Generate game_id first
        game_id = generate_game_id()

        state = PokerStateManager(
            config=poker_config,
            tournament_config=tournament_config,
            game_id=game_id,
            seed=11111,
        )

        # Initialize
        state.initialize()

        expected_file = data_dir / f"events_{game_id}.jsonl"
        transport = MockTransport(output_file=expected_file, store_events=True)

        event_publisher = FrontEndEventPublisher(
            transport=transport,
            game_id=game_id,
            buffer_events=True,
        )

        # Create fresh runner for orchestrator
        state2 = PokerStateManager(
            config=poker_config,
            tournament_config=tournament_config,
            game_id=game_id,
            seed=11111,
        )
        action_provider = BotActionProvider.with_seed(789)

        orchestrator = PokerOrchestrator(
            state=state2,
            action_provider=action_provider,
            event_publisher=event_publisher,
            max_hands=10,
        )

        # Act
        await orchestrator.run_game()
        await transport.close()

        # Assert
        assert expected_file.exists()

        # Verify content
        with expected_file.open("r") as f:
            lines = [line.strip() for line in f if line.strip()]
        assert len(lines) > 0

        print(f"\n=== File Path Verification ===")
        print(f"Expected: {expected_file}")
        print(f"Exists: {expected_file.exists()}")
        print(f"Events written: {len(lines)}")
