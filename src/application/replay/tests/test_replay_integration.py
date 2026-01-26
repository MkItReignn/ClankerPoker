from pathlib import Path

import pytest

from src.application.poker.context import PokerDecisionContext
from src.application.poker.game_factory import RuntimeConfig
from src.application.poker.orchestration import (
    PokerOrchestrator,
    PokerStateManager,
)
from src.application.poker.records.models import GameRecord
from src.application.poker.state_observers.details import HandOutcomeDetails
from src.application.protocols.player import PlayerConfig
from src.application.replay import ReplayActionProvider
from src.application.replay.tests.conftest import StubGameObserver
from src.domain.models.game import Game


class TestReplayDeterminism:
    @pytest.mark.asyncio
    async def test_replay_produces_same_number_of_hands(
        self,
        default_record: GameRecord,
        default_runtime_config: RuntimeConfig,
    ) -> None:
        state = PokerStateManager(
            config=default_runtime_config.poker_config,
            tournament_config=default_runtime_config.tournament_config,
            game_id=default_runtime_config.game_id,
            seed=default_runtime_config.seed,
            repository=None,
        )

        orchestrator = PokerOrchestrator(
            state=state,
            action_provider=default_runtime_config.action_provider,
        )

        result = await orchestrator.run_game()

        assert result.total_hands == len(default_record.completed_hands)

    @pytest.mark.asyncio
    async def test_replay_hand_winners_match(
        self,
        default_record: GameRecord,
        default_runtime_config: RuntimeConfig,
    ) -> None:
        replayed_outcomes: list[tuple[str, ...]] = []

        state = PokerStateManager(
            config=default_runtime_config.poker_config,
            tournament_config=default_runtime_config.tournament_config,
            game_id=default_runtime_config.game_id,
            seed=default_runtime_config.seed,
            repository=None,
        )

        class OutcomeCapture(StubGameObserver):
            async def on_hand_completed(
                self, game: Game, details: HandOutcomeDetails
            ) -> None:
                winner_ids: tuple[str, ...] = tuple(
                    winner.player_id for winner in details.winners
                )
                replayed_outcomes.append(winner_ids)

        capture = OutcomeCapture()
        state._notifier.add_observer(capture)

        orchestrator = PokerOrchestrator(
            state=state,
            action_provider=default_runtime_config.action_provider,
        )

        await orchestrator.run_game()

        for i, (replayed, original) in enumerate(
            zip(replayed_outcomes, default_record.completed_hands, strict=True)
        ):
            assert original.outcome is not None
            original_winners: tuple[str, ...] = tuple(
                winner.player_id for winner in original.outcome.winners
            )
            assert replayed == original_winners, (
                f"Hand {i + 1}: winners mismatch. "
                f"Replayed: {replayed}, Original: {original_winners}"
            )

    @pytest.mark.asyncio
    async def test_replay_pot_amounts_match(
        self,
        default_record: GameRecord,
        default_runtime_config: RuntimeConfig,
    ) -> None:
        replayed_pots: list[int] = []

        state = PokerStateManager(
            config=default_runtime_config.poker_config,
            tournament_config=default_runtime_config.tournament_config,
            game_id=default_runtime_config.game_id,
            seed=default_runtime_config.seed,
            repository=None,
        )

        class PotCapture(StubGameObserver):
            async def on_hand_completed(
                self, game: Game, details: HandOutcomeDetails
            ) -> None:
                replayed_pots.append(details.pot_amount.value)

        capture = PotCapture()
        state._notifier.add_observer(capture)

        orchestrator = PokerOrchestrator(
            state=state,
            action_provider=default_runtime_config.action_provider,
        )

        _ = await orchestrator.run_game()

        for i, (replayed_pot, original_hand) in enumerate(
            zip(replayed_pots, default_record.completed_hands, strict=True)
        ):
            assert original_hand.outcome is not None
            original_pot: int = original_hand.outcome.pot_amount.value
            assert replayed_pot == original_pot, (
                f"Hand {i + 1}: pot mismatch. "
                f"Replayed: {replayed_pot}, Original: {original_pot}"
            )

    @pytest.mark.asyncio
    async def test_replay_game_winner_matches(
        self,
        default_record: GameRecord,
        default_runtime_config: RuntimeConfig,
    ) -> None:
        state = PokerStateManager(
            config=default_runtime_config.poker_config,
            tournament_config=default_runtime_config.tournament_config,
            game_id=default_runtime_config.game_id,
            seed=default_runtime_config.seed,
            repository=None,
        )

        orchestrator = PokerOrchestrator(
            state=state,
            action_provider=default_runtime_config.action_provider,
        )

        result = await orchestrator.run_game()

        # Find original winner (player with chips remaining at end)
        original_winner_id: str | None = None
        for player_id, player_record in default_record.player_records.items():
            if (
                player_record.chips.value > 0
                and not player_record.is_eliminated
            ):
                original_winner_id = player_id
                break

        assert result.winner_id == original_winner_id

    @pytest.mark.asyncio
    async def test_replay_exhausts_all_actions(
        self,
        default_runtime_config: RuntimeConfig,
    ) -> None:
        provider = default_runtime_config.action_provider
        assert isinstance(provider, ReplayActionProvider)

        initial_actions: int = provider.remaining_actions

        state = PokerStateManager(
            config=default_runtime_config.poker_config,
            tournament_config=default_runtime_config.tournament_config,
            game_id=default_runtime_config.game_id,
            seed=default_runtime_config.seed,
            repository=None,
        )

        orchestrator = PokerOrchestrator(
            state=state,
            action_provider=provider,
        )

        _ = await orchestrator.run_game()

        assert provider.remaining_actions == 0, (
            f"Not all actions consumed. "
            f"Started with {initial_actions}, {provider.remaining_actions} remaining"
        )


class TestReplayActionProvider:
    def test_filters_blind_actions(self, default_record: GameRecord) -> None:
        provider: ReplayActionProvider = ReplayActionProvider(default_record)

        # Count blind actions in record
        blind_count: int = 0
        total_turns: int = 0
        for hand in default_record.completed_hands:
            for round_rec in hand.rounds:
                for turn in round_rec.turns:
                    total_turns += 1
                    if turn.action.action_type.is_blind_action:
                        blind_count += 1

        expected_actions: int = total_turns - blind_count
        assert provider.remaining_actions == expected_actions

    @pytest.mark.asyncio
    async def test_remaining_actions_decrements(
        self,
        default_record: GameRecord,
        stub_player_config: PlayerConfig,
        stub_context: PokerDecisionContext,
    ) -> None:
        provider: ReplayActionProvider = ReplayActionProvider(default_record)
        initial: int = provider.remaining_actions

        _ = await provider.get_action(stub_context, [], stub_player_config)
        _ = await provider.get_action(stub_context, [], stub_player_config)

        assert provider.remaining_actions == initial - 2

    @pytest.mark.asyncio
    async def test_actions_played_increments(
        self,
        default_record: GameRecord,
        stub_player_config: PlayerConfig,
        stub_context: PokerDecisionContext,
    ) -> None:
        provider: ReplayActionProvider = ReplayActionProvider(default_record)
        assert provider.actions_played == 0

        _ = await provider.get_action(stub_context, [], stub_player_config)
        assert provider.actions_played == 1

        _ = await provider.get_action(stub_context, [], stub_player_config)
        assert provider.actions_played == 2


class TestRecordLoader:
    def test_load_valid_record(self, default_replay_path: Path) -> None:
        from src.application.replay import RecordLoader

        record: GameRecord = RecordLoader.load(default_replay_path)

        assert record.game_id is not None
        assert record.metadata.seed is not None
        assert len(record.player_records) > 0
        assert len(record.completed_hands) > 0

    def test_load_nonexistent_file_raises(self) -> None:
        from src.application.replay import RecordLoader, RecordLoadError

        with pytest.raises(RecordLoadError, match="not found"):
            _ = RecordLoader.load(Path("nonexistent/file.json"))

    def test_load_invalid_json_raises(self, tmp_path: Path) -> None:
        from src.application.replay import RecordLoader, RecordLoadError

        bad_file: Path = tmp_path / "bad.json"
        _ = bad_file.write_text("{ invalid json }")

        with pytest.raises(RecordLoadError, match="Invalid JSON"):
            _ = RecordLoader.load(bad_file)
