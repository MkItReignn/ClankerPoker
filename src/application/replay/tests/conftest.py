from dataclasses import dataclass
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
from src.application.poker.records.models import (
    GameRecord,
    HandRecord,
    RoundRecord,
    TurnRecord,
)
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


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    equal: bool
    message: str = ""

    @classmethod
    def success(cls) -> "ComparisonResult":
        return cls(equal=True)

    @classmethod
    def failure(cls, message: str) -> "ComparisonResult":
        return cls(equal=False, message=message)


class RecordComparator:
    @staticmethod
    def compare_games(
        original: GameRecord, replayed: GameRecord
    ) -> ComparisonResult:
        if original.game_id != replayed.game_id:
            return ComparisonResult.failure(
                f"game_id mismatch: {original.game_id} vs {replayed.game_id}"
            )

        if original.metadata.seed != replayed.metadata.seed:
            return ComparisonResult.failure(
                f"seed mismatch: {original.metadata.seed} vs {replayed.metadata.seed}"
            )

        if len(original.completed_hands) != len(replayed.completed_hands):
            return ComparisonResult.failure(
                f"completed_hands count: {len(original.completed_hands)} vs "
                f"{len(replayed.completed_hands)}"
            )

        for i, (orig_hand, repl_hand) in enumerate(
            zip(
                original.completed_hands, replayed.completed_hands, strict=True
            )
        ):
            result = RecordComparator.compare_hands(
                orig_hand, repl_hand, i + 1
            )
            if not result.equal:
                return result

        return ComparisonResult.success()

    @staticmethod
    def compare_hands(
        original: HandRecord, replayed: HandRecord, hand_num: int
    ) -> ComparisonResult:
        if original.hand_number != replayed.hand_number:
            return ComparisonResult.failure(
                f"Hand {hand_num}: hand_number mismatch"
            )

        if original.button_seat != replayed.button_seat:
            return ComparisonResult.failure(
                f"Hand {hand_num}: button_seat mismatch"
            )

        if original.blinds != replayed.blinds:
            return ComparisonResult.failure(
                f"Hand {hand_num}: blinds mismatch"
            )

        if len(original.rounds) != len(replayed.rounds):
            return ComparisonResult.failure(
                f"Hand {hand_num}: rounds count {len(original.rounds)} vs "
                f"{len(replayed.rounds)}"
            )

        for j, (orig_round, repl_round) in enumerate(
            zip(original.rounds, replayed.rounds, strict=True)
        ):
            result = RecordComparator.compare_rounds(
                orig_round, repl_round, hand_num, j + 1
            )
            if not result.equal:
                return result

        if (original.outcome is None) != (replayed.outcome is None):
            return ComparisonResult.failure(
                f"Hand {hand_num}: outcome presence mismatch"
            )

        if original.outcome and replayed.outcome:
            if original.outcome.pot_amount != replayed.outcome.pot_amount:
                return ComparisonResult.failure(
                    f"Hand {hand_num}: pot_amount mismatch "
                    f"{original.outcome.pot_amount} vs {replayed.outcome.pot_amount}"
                )

            orig_winners = tuple(w.player_id for w in original.outcome.winners)
            repl_winners = tuple(w.player_id for w in replayed.outcome.winners)
            if orig_winners != repl_winners:
                return ComparisonResult.failure(
                    f"Hand {hand_num}: winners mismatch {orig_winners} vs {repl_winners}"
                )

        return ComparisonResult.success()

    @staticmethod
    def compare_rounds(
        original: RoundRecord,
        replayed: RoundRecord,
        hand_num: int,
        round_num: int,
    ) -> ComparisonResult:
        ctx = f"Hand {hand_num}, Round {round_num}"

        if original.phase != replayed.phase:
            return ComparisonResult.failure(f"{ctx}: phase mismatch")

        if original.community_cards != replayed.community_cards:
            return ComparisonResult.failure(f"{ctx}: community_cards mismatch")

        if len(original.turns) != len(replayed.turns):
            return ComparisonResult.failure(
                f"{ctx}: turns count {len(original.turns)} vs {len(replayed.turns)}"
            )

        for k, (orig_turn, repl_turn) in enumerate(
            zip(original.turns, replayed.turns, strict=True)
        ):
            result = RecordComparator.compare_turns(
                orig_turn, repl_turn, hand_num, round_num, k + 1
            )
            if not result.equal:
                return result

        return ComparisonResult.success()

    @staticmethod
    def compare_turns(
        original: TurnRecord,
        replayed: TurnRecord,
        hand_num: int,
        round_num: int,
        turn_num: int,
    ) -> ComparisonResult:
        ctx = f"Hand {hand_num}, Round {round_num}, Turn {turn_num}"

        if original.action.player_id != replayed.action.player_id:
            return ComparisonResult.failure(f"{ctx}: player_id mismatch")

        if original.action.action_type != replayed.action.action_type:
            return ComparisonResult.failure(
                f"{ctx}: action_type {original.action.action_type} vs "
                f"{replayed.action.action_type}"
            )

        if original.action.amount != replayed.action.amount:
            return ComparisonResult.failure(
                f"{ctx}: amount {original.action.amount} vs {replayed.action.amount}"
            )

        orig_narration = (
            original.narration.thought_process if original.narration else None
        )
        repl_narration = (
            replayed.narration.thought_process if replayed.narration else None
        )
        if orig_narration != repl_narration:
            return ComparisonResult.failure(f"{ctx}: narration mismatch")

        return ComparisonResult.success()


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
