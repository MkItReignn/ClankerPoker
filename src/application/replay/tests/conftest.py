from pathlib import Path

import pytest

from src.application.poker.context import PokerDecisionContext
from src.application.poker.context.types import (
    ActingPlayerState,
    CurrentHandRecord,
    HandState,
    PreviousHandsRecord,
)
from src.application.poker.game_factory import (
    RuntimeConfig,
    RuntimeConfigFactory,
)
from src.application.poker.records.models import GameRecord
from src.application.poker.state_observers.details import (
    ActionAppliedDetails,
    BlindsPostedDetails,
    GameCompletedDetails,
    GameStartedDetails,
    HandOutcomeDetails,
    HandStartedDetails,
    HoleCardsDealtDetails,
    RoundCompletedDetails,
    RoundStartedDetails,
)
from src.application.protocols.player import PlayerConfig
from src.application.replay import RecordLoader
from src.domain.models.blinds import BlindLevel
from src.domain.models.card import Card, Rank, Suit
from src.domain.models.chips import ChipAmount
from src.domain.models.game import Game, HandPhase
from src.domain.models.hand import Hand
from src.domain.models.llm_model import LlmModel

FIXTURES_DIR: Path = Path(__file__).parent / "fixtures"
TEST_RECORD_PATH: Path = FIXTURES_DIR / "test_record.json"


class StubGameObserver:
    """Base observer with no-op implementations for all game events."""

    async def on_game_started(
        self, game: Game, details: GameStartedDetails
    ) -> None:
        pass

    async def on_game_completed(
        self, game: Game, details: GameCompletedDetails
    ) -> None:
        pass

    async def on_hand_started(
        self, game: Game, details: HandStartedDetails
    ) -> None:
        pass

    async def on_hand_completed(
        self, game: Game, details: HandOutcomeDetails
    ) -> None:
        pass

    async def on_round_started(
        self, game: Game, details: RoundStartedDetails
    ) -> None:
        pass

    async def on_round_completed(
        self, game: Game, details: RoundCompletedDetails
    ) -> None:
        pass

    async def on_blinds_posted(
        self, game: Game, details: BlindsPostedDetails
    ) -> None:
        pass

    async def on_hole_cards_dealt(
        self, game: Game, details: HoleCardsDealtDetails
    ) -> None:
        pass

    async def on_action_applied(
        self, game: Game, details: ActionAppliedDetails
    ) -> None:
        pass


@pytest.fixture
def default_replay_path() -> Path:
    return TEST_RECORD_PATH


@pytest.fixture
def default_record(default_replay_path: Path) -> GameRecord:
    return RecordLoader.load(default_replay_path)


@pytest.fixture
def default_runtime_config(default_replay_path: Path) -> RuntimeConfig:
    return RuntimeConfigFactory.for_replay(default_replay_path)


@pytest.fixture
def stub_player_config() -> PlayerConfig:
    return PlayerConfig(
        player_id="test_player",
        name="Test Player",
        llm_model=LlmModel.NONE,
    )


@pytest.fixture
def stub_context() -> PokerDecisionContext:
    stub_hand = Hand(
        card1=Card(Suit.SPADES, Rank.ACE),
        card2=Card(Suit.HEARTS, Rank.KING),
    )
    return PokerDecisionContext(
        acting_player=ActingPlayerState(
            player_id="test_player",
            player_name="Test Player",
            hole_cards=stub_hand,
            position=None,
            stack=ChipAmount(10000),
        ),
        hand_state=HandState(
            phase=HandPhase.PRE_FLOP,
            community_cards=(),
            pot_total=ChipAmount(150),
            hand_number=1,
            current_bet=ChipAmount(100),
            blinds=BlindLevel(
                small_blind=ChipAmount(50),
                big_blind=ChipAmount(100),
                level=1,
            ),
        ),
        opponents=(),
        current_hand_record=CurrentHandRecord(text=""),
        previous_hands_record=PreviousHandsRecord(text=""),
    )
