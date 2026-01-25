"""Pytest fixtures for PokerStateManager integration tests.

These fixtures support behavioral testing of the state manager by providing:
- State manager factories with configurable tournament settings
- A mock action provider that returns predetermined actions
- Player and configuration factories
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from src.application.poker.orchestration.state_manager import PokerStateManager
from src.application.protocols.player import ActionResponse, PlayerConfig
from src.config.blind_schedule.config import BlindSchedule, BlindScheduleEntry
from src.config.poker.config import PokerGameConfig, PokerPlayerConfig
from src.config.tournament.config import PayoutStructure, TournamentConfig
from src.domain.models.actions import Action, ActionType
from src.domain.models.available_action import AvailableActions
from src.domain.models.blinds import BlindLevel
from src.domain.models.chips import ChipAmount
from src.domain.models.llm_model import LlmModel
from src.domain.models.narration import Narration

SMALL_BLIND = ChipAmount(10)
BIG_BLIND = ChipAmount(20)
STARTING_CHIPS = ChipAmount(1000)
TEST_SEED = 42
TEST_GAME_ID = "game-test1234"


@pytest.fixture
def player_names() -> dict[str, str]:
    """Standard player names mapping."""
    return {
        "player-1": "Alice",
        "player-2": "Bob",
        "player-3": "Charlie",
    }


@pytest.fixture
def poker_game_config(player_names: dict[str, str]) -> PokerGameConfig:
    """Game configuration with player configs."""
    player_configs = {
        player_id: PokerPlayerConfig(
            player_id=player_id,
            name=name,
            model_id=LlmModel.OPENAI_GPT4O_MINI,
        )
        for player_id, name in player_names.items()
    }
    return PokerGameConfig(player_configs=player_configs)


@pytest.fixture
def tournament_config() -> TournamentConfig:
    """Standard tournament config for tests."""
    return TournamentConfig(
        buy_in_amount=ChipAmount(1000),
        starting_chip_stack=STARTING_CHIPS,
        payout_structure=PayoutStructure.WINNER_TAKES_ALL,
        blind_schedule=BlindSchedule(
            entries=(
                BlindScheduleEntry(
                    level=BlindLevel(
                        small_blind=SMALL_BLIND,
                        big_blind=BIG_BLIND,
                        level=1,
                    ),
                    start_hand=1,
                    duration_hands=100,
                ),
            )
        ),
    )


def create_two_player_config() -> PokerGameConfig:
    """Create config for 2-player games."""
    player_configs = {
        "player-1": PokerPlayerConfig(
            player_id="player-1",
            name="Alice",
            model_id=LlmModel.OPENAI_GPT4O_MINI,
        ),
        "player-2": PokerPlayerConfig(
            player_id="player-2",
            name="Bob",
            model_id=LlmModel.OPENAI_GPT4O_MINI,
        ),
    }
    return PokerGameConfig(player_configs=player_configs)


def create_three_player_config() -> PokerGameConfig:
    """Create config for 3-player games."""
    player_configs = {
        "player-1": PokerPlayerConfig(
            player_id="player-1",
            name="Alice",
            model_id=LlmModel.OPENAI_GPT4O_MINI,
        ),
        "player-2": PokerPlayerConfig(
            player_id="player-2",
            name="Bob",
            model_id=LlmModel.OPENAI_GPT4O_MINI,
        ),
        "player-3": PokerPlayerConfig(
            player_id="player-3",
            name="Charlie",
            model_id=LlmModel.OPENAI_GPT4O_MINI,
        ),
    }
    return PokerGameConfig(player_configs=player_configs)


@pytest.fixture
def two_player_config() -> PokerGameConfig:
    """Config for 2-player games."""
    return create_two_player_config()


@pytest.fixture
def three_player_config() -> PokerGameConfig:
    """Config for 3-player games."""
    return create_three_player_config()


@pytest.fixture
def poker_state(
    two_player_config: PokerGameConfig,
    tournament_config: TournamentConfig,
) -> PokerStateManager:
    """Create a PokerStateManager with test configuration for 2 players."""
    return PokerStateManager(
        config=two_player_config,
        tournament_config=tournament_config,
        game_id=TEST_GAME_ID,
        seed=TEST_SEED,
    )


@pytest.fixture
def three_player_state(
    three_player_config: PokerGameConfig,
    tournament_config: TournamentConfig,
) -> PokerStateManager:
    """Create a PokerStateManager with test configuration for 3 players."""
    return PokerStateManager(
        config=three_player_config,
        tournament_config=tournament_config,
        game_id=TEST_GAME_ID,
        seed=TEST_SEED,
    )


class ScriptedActionProvider:
    """Action provider that returns actions from a predetermined script.

    This is the mock at the LLM boundary - the only external dependency.

    Supports two modes:
    1. Sequential actions: Pass a list of actions, consumed in order by any player.
    2. Per-player actions: Pass a dict mapping player_id to list of actions,
       each player gets actions from their own list.
    """

    def __init__(
        self,
        actions: list[Action] | dict[str, list[Action]],
    ) -> None:
        if isinstance(actions, dict):
            self._per_player_actions = {pid: list(acts) for pid, acts in actions.items()}
            self._per_player_indices: dict[str, int] = {pid: 0 for pid in actions.keys()}
            self._actions: list[Action] | None = None
            self._index = 0
        else:
            self._actions = list(actions)
            self._index = 0
            self._per_player_actions: dict[str, list[Action]] | None = None
            self._per_player_indices: dict[str, int] | None = None

    @property
    def actions_taken(self) -> int:
        """Number of actions consumed from the script."""
        if self._per_player_actions is not None:
            return sum(self._per_player_indices.values())
        return self._index

    @property
    def actions_remaining(self) -> int:
        """Number of actions left in the script."""
        if self._per_player_actions is not None:
            total = sum(len(acts) for acts in self._per_player_actions.values())
            return total - self.actions_taken
        return len(self._actions) - self._index

    async def __aenter__(self) -> "ScriptedActionProvider":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        pass

    async def get_action(
        self,
        context: Any,
        available_actions: list[AvailableActions],
        config: PlayerConfig,
    ) -> ActionResponse[Action, None]:
        return await self(context, available_actions, config)

    async def __call__(
        self,
        context: Any,
        available_actions: list[AvailableActions],
        config: PlayerConfig,
    ) -> ActionResponse[Action, None]:
        """Return the next scripted action for the requesting player."""
        if self._per_player_actions is not None:
            player_actions = self._per_player_actions.get(config.player_id)
            if player_actions is None:
                raise RuntimeError(
                    f"No actions configured for player {config.player_id}. "
                    f"Available players: {list(self._per_player_actions.keys())}"
                )

            player_index = self._per_player_indices[config.player_id]
            if player_index >= len(player_actions):
                raise RuntimeError(
                    f"Script exhausted for player {config.player_id} after {player_index} actions. "
                    f"Player requested action but none available."
                )

            requested_action = player_actions[player_index]

            # If the requested action is not available, try to find a compatible one
            # (e.g., if CALL requested but only CHECK available, use CHECK)
            action = self._find_compatible_action(requested_action, available_actions)

            self._per_player_indices[config.player_id] = player_index + 1
            return ActionResponse(action=action, narration=None)

        if self._index >= len(self._actions):
            raise RuntimeError(
                f"Script exhausted after {self._index} actions. "
                f"Player {config.player_id} requested action but none available."
            )

        requested_action = self._actions[self._index]
        action = self._find_compatible_action(requested_action, available_actions)
        self._index += 1
        return ActionResponse(action=action, narration=None)

    def _find_compatible_action(
        self,
        requested: Action,
        available_actions: list[AvailableActions],
    ) -> Action:
        """Find a compatible action if the requested one is not available.

        Handles cases like CALL vs CHECK (both mean "match the current bet").
        """
        from src.domain.models.available_action import (AvailableCallAction,
                                                        AvailableCheckAction)

        # Check if requested action is available
        for available in available_actions:
            if available.action_type == requested.action_type:
                return requested

        # If CALL requested but only CHECK available (or vice versa), use what's available
        if requested.action_type == ActionType.CALL:
            for available in available_actions:
                if isinstance(available, AvailableCheckAction):
                    return Action(action_type=ActionType.CHECK)
        elif requested.action_type == ActionType.CHECK:
            for available in available_actions:
                if isinstance(available, AvailableCallAction):
                    return Action(action_type=ActionType.CALL, amount=available.call_amount)

        # No compatible action found, return requested (will fail validation with clear error)
        return requested


@pytest.fixture
def scripted_provider_factory() -> (
    Callable[[list[Action] | dict[str, list[Action]]], ScriptedActionProvider]
):
    """Factory to create scripted action providers.

    Accepts either:
    - list[Action]: Sequential actions consumed by any player
    - dict[str, list[Action]]: Per-player actions, keyed by player_id
    """

    def create_provider(actions: list[Action] | dict[str, list[Action]]) -> ScriptedActionProvider:
        return ScriptedActionProvider(actions)

    return create_provider


def fold() -> Action:
    """Create a fold action."""
    return Action(action_type=ActionType.FOLD)


def check() -> Action:
    """Create a check action."""
    return Action(action_type=ActionType.CHECK)


def call() -> Action:
    """Create a call action."""
    return Action(action_type=ActionType.CALL)


def bet(amount: int) -> Action:
    """Create a bet action."""
    return Action(action_type=ActionType.BET, amount=ChipAmount(amount))


def raise_to(amount: int) -> Action:
    """Create a raise action."""
    return Action(action_type=ActionType.RAISE, amount=ChipAmount(amount))


def all_in(amount: int) -> Action:
    """Create an all-in action."""
    return Action(action_type=ActionType.ALL_IN, amount=ChipAmount(amount))


async def run_turn(
    state: PokerStateManager,
    action_provider: ScriptedActionProvider,
) -> bool:
    """Run a single turn - get action from provider and apply it.

    Returns True if a turn was executed, False if no player to act.
    """
    player_id = state.get_player_to_act_id()
    if player_id is None:
        return False

    config = state.get_player_config(player_id)
    context = state.build_context(player_id)
    available_actions = state.get_available_actions(player_id)

    response = await action_provider.get_action(context, available_actions, config)

    await state.apply_action(player_id, response)
    return True
