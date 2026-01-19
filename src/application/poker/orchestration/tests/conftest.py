"""Pytest fixtures for PokerGameRunner integration tests.

These fixtures support behavioral testing of the game runner by providing:
- Game state factories for various starting conditions
- A mock action provider that returns predetermined actions
- Player and configuration factories
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, UTC
from typing import Any

import pytest

from src.application.protocols.player import ActionResponse, PlayerConfig
from src.application.poker.orchestration.runner import PokerGameRunner
from src.config.blind_schedule.config import BlindSchedule, BlindScheduleEntry
from src.config.poker.config import PokerGameConfig, PokerPlayerConfig
from src.config.tournament.config import PayoutStructure, TournamentConfig
from src.domain.models.actions import Action, ActionType
from src.domain.models.available_action import AvailableActions
from src.domain.models.blinds import BlindLevel
from src.domain.models.bot import Bot, BotId, BotType, Prompt
from src.domain.models.chips import ChipAmount
from src.domain.models.game import (BettingState, BlindState, Game,
                                    GameIdentity, GamePhase, GameStatus,
                                    HandState)
from src.domain.models.llm_model import LlmModel
from src.domain.models.player import (BettingRoundActionStatus,
                                      HandParticipationStatus, Player,
                                      PlayerId)
from src.domain.models.players import Players
from src.domain.models.pot import Pot, PotState
from src.domain.models.seat import Seat

SMALL_BLIND = ChipAmount(10)
BIG_BLIND = ChipAmount(20)
STARTING_CHIPS = ChipAmount(1000)
TEST_SEED = 42


@pytest.fixture
def sample_bot() -> Bot:
    """A sample bot for creating players."""
    return Bot(
        id=BotId("test-bot-1"),
        name="Test Bot",
        bot_type=BotType.HOUSE,
        llm_model=LlmModel.OPENAI_GPT4O_MINI,
        system_prompt=Prompt("You are a test bot."),
    )


@pytest.fixture
def player_factory(sample_bot: Bot) -> Callable[..., Player]:
    """Factory to create players with configurable properties."""

    def create_player(
        player_id: PlayerId,
        seat: Seat,
        remaining_chips: ChipAmount = STARTING_CHIPS,
        total_invested_this_hand: ChipAmount | None = None,
        participation_status: HandParticipationStatus = HandParticipationStatus.IN_HAND,
        betting_status: BettingRoundActionStatus = BettingRoundActionStatus.NEEDS_ACTION,
    ) -> Player:
        if total_invested_this_hand is None:
            total_invested_this_hand = ChipAmount(0)

        return Player(
            id=player_id,
            bot_id=sample_bot.id,
            seat=seat,
            remaining_chips=remaining_chips,
            hole_cards=None,
            betting_status=betting_status,
            participation_status=participation_status,
            total_invested_this_hand=total_invested_this_hand,
        )

    return create_player


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


@pytest.fixture
def waiting_game_factory(
    tournament_config: TournamentConfig,
) -> Callable[..., Game]:
    """Factory to create games in WAITING status for initialization tests."""

    def create_game(
        players: list[Player],
        seed: int = TEST_SEED,
    ) -> Game:
        now = datetime.now(UTC)
        return Game(
            identity=GameIdentity(
                id="test-game-1",
                created_at=now,
                updated_at=now,
                started_at=None,
                completed_at=None,
                status=GameStatus.WAITING,
                seed=seed,
            ),
            tournament_config=tournament_config,
            hand_state=HandState(
                hand_number=1,
                current_phase=GamePhase.PRE_FLOP,
                community_cards=[],
                is_initial_hand_setup=True,
            ),
            pot_state=PotState(
                main_pot=Pot(
                    amount=ChipAmount(0),
                    eligible_player_ids=frozenset({p.id for p in players}),
                ),
                side_pots=[],
            ),
            betting_state=BettingState(
                last_raise_increment=ChipAmount(0),
                position_to_act=0,
            ),
            button_seat=Seat.SEAT_0,
            blind_state=BlindState(
                current_blind_level=BlindLevel(
                    small_blind=SMALL_BLIND,
                    big_blind=BIG_BLIND,
                    level=1,
                )
            ),
            players=Players.from_list(players),
            results=None,
        )

    return create_game


@pytest.fixture
def two_player_waiting_game(
    player_factory: Callable[..., Player],
    waiting_game_factory: Callable[..., Game],
) -> Game:
    """A 2-player game in WAITING status ready for initialization."""
    players = [
        player_factory(player_id="player-1", seat=Seat.SEAT_0),
        player_factory(player_id="player-2", seat=Seat.SEAT_1),
    ]
    return waiting_game_factory(players=players)


@pytest.fixture
def three_player_waiting_game(
    player_factory: Callable[..., Player],
    waiting_game_factory: Callable[..., Game],
) -> Game:
    """A 3-player game in WAITING status ready for initialization."""
    players = [
        player_factory(player_id="player-1", seat=Seat.SEAT_0),
        player_factory(player_id="player-2", seat=Seat.SEAT_1),
        player_factory(player_id="player-3", seat=Seat.SEAT_2),
    ]
    return waiting_game_factory(players=players)


@pytest.fixture
def poker_runner(poker_game_config: PokerGameConfig) -> PokerGameRunner:
    """Create a PokerGameRunner with test configuration."""
    return PokerGameRunner(config=poker_game_config)


class ScriptedActionProvider:
    """Action provider that returns actions from a predetermined script.

    This is the mock at the LLM boundary - the only external dependency.
    Actions are consumed in order; raises if script is exhausted.
    """

    def __init__(self, actions: list[Action]) -> None:
        self._actions = list(actions)
        self._index = 0

    @property
    def actions_taken(self) -> int:
        """Number of actions consumed from the script."""
        return self._index

    @property
    def actions_remaining(self) -> int:
        """Number of actions left in the script."""
        return len(self._actions) - self._index

    async def __call__(
        self,
        context: Any,
        available_actions: list[AvailableActions],
        config: PlayerConfig,
    ) -> ActionResponse[Action, None]:
        """Return the next scripted action."""
        if self._index >= len(self._actions):
            raise RuntimeError(
                f"Script exhausted after {self._index} actions. "
                f"Player {config.player_id} requested action but none available."
            )

        action = self._actions[self._index]
        self._index += 1
        return ActionResponse(action=action, narration=None)


@pytest.fixture
def scripted_provider_factory() -> Callable[[list[Action]], ScriptedActionProvider]:
    """Factory to create scripted action providers."""

    def create_provider(actions: list[Action]) -> ScriptedActionProvider:
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
