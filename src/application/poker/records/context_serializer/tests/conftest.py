"""Fixtures for context serializer tests."""

from datetime import datetime

import pytest

from src.application.poker.records.models import (
    ActionRecord,
    GameMetadata,
    GameRecord,
    HandLevelPlayerRecord,
    HandRecord,
    RoundLevelPlayerRecord,
    RoundRecord,
    TurnRecord,
)
from src.application.poker.state_observers.details import (
    EliminatedInfo,
    HandOutcomeDetails,
    PlayerOutcome,
    ShowdownResult,
    WinnerInfo,
)
from src.config.blind_schedule.config import BlindSchedule, BlindScheduleEntry
from src.config.tournament.config import PayoutStructure
from src.domain.models.actions import ActionType
from src.domain.models.blinds import BlindLevel
from src.domain.models.card import Card, Rank, Suit
from src.domain.models.chips import ChipAmount
from src.domain.models.game import HandPhase
from src.domain.models.hand import Hand
from src.domain.models.llm_model import LlmModel
from src.domain.models.player import HandParticipationStatus
from src.domain.models.position import PositionName
from src.domain.models.seat import Seat
from src.domain.rules.hand_evaluator import HandEvaluation, HandRank


@pytest.fixture
def default_blind_level() -> BlindLevel:
    return BlindLevel(
        small_blind=ChipAmount(25), big_blind=ChipAmount(50), level=1
    )


@pytest.fixture
def default_blind_schedule(default_blind_level: BlindLevel) -> BlindSchedule:
    return BlindSchedule(
        entries=(
            BlindScheduleEntry(
                level=default_blind_level,
                start_hand=1,
                duration_hands=100,
            ),
        )
    )


@pytest.fixture
def default_game_metadata(
    default_blind_schedule: BlindSchedule,
) -> GameMetadata:
    return GameMetadata(
        seed=42,
        buy_in_amount=ChipAmount(100),
        starting_chip_stack=ChipAmount(1000),
        blind_schedule=default_blind_schedule,
        payout_structure=PayoutStructure.WINNER_TAKES_ALL,
        started_at=datetime(2024, 1, 1, 12, 0, 0),
    )


def make_hand_level_player_record(
    player_id: str,
    player_name: str,
    seat: Seat,
    position: PositionName,
    chips: int = 1000,
    starting_chips: int = 1000,
    hole_cards: Hand | None = None,
) -> HandLevelPlayerRecord:
    """Create a HandLevelPlayerRecord for testing."""
    return HandLevelPlayerRecord(
        player_id=player_id,
        player_name=player_name,
        seat=seat,
        chips=ChipAmount(chips),
        llm_model=LlmModel.NONE,
        hole_cards=hole_cards,
        position=position,
        starting_chips=ChipAmount(starting_chips),
    )


def make_round_level_player_record(
    player_id: str,
    player_name: str,
    seat: Seat,
    chips: int = 1000,
    chips_at_round_start: int = 1000,
    total_invested: int = 0,
) -> RoundLevelPlayerRecord:
    """Create a RoundLevelPlayerRecord for testing."""
    return RoundLevelPlayerRecord(
        player_id=player_id,
        player_name=player_name,
        seat=seat,
        chips=ChipAmount(chips),
        llm_model=LlmModel.NONE,
        chips_at_round_start=ChipAmount(chips_at_round_start),
        total_invested_in_hand_at_round_start=ChipAmount(total_invested),
        participation_status=HandParticipationStatus.IN_HAND,
        is_all_in=False,
    )


def make_action_record(
    player_id: str,
    player_name: str,
    action_type: ActionType,
    amount: int | None = None,
    phase: HandPhase = HandPhase.PRE_FLOP,
) -> ActionRecord:
    """Create an ActionRecord for testing."""
    return ActionRecord(
        player_id=player_id,
        player_name=player_name,
        phase=phase,
        action_type=action_type,
        amount=ChipAmount(amount) if amount is not None else None,
        timestamp=datetime.now(),
    )


def make_turn_record(
    player_id: str,
    player_name: str,
    action_type: ActionType,
    amount: int | None = None,
    phase: HandPhase = HandPhase.PRE_FLOP,
    turn_number: int = 1,
) -> TurnRecord:
    return TurnRecord(
        round_turn_number=turn_number,
        action=make_action_record(
            player_id, player_name, action_type, amount, phase
        ),
        timestamp=datetime.now(),
    )


def make_hand_record(
    hand_number: int,
    player_records: dict[str, HandLevelPlayerRecord],
    rounds: list[RoundRecord] | None = None,
    outcome: HandOutcomeDetails | None = None,
) -> HandRecord:
    """Create a HandRecord for testing."""
    hand = HandRecord(
        hand_number=hand_number,
        button_seat=Seat.SEAT_0,
        blinds=BlindLevel(
            small_blind=ChipAmount(25),
            big_blind=ChipAmount(50),
            level=1,
        ),
        player_records=player_records,
    )
    if rounds:
        hand.rounds = rounds
    if outcome:
        hand.outcome = outcome
    return hand


def make_round_record(
    phase: HandPhase,
    player_records: dict[str, RoundLevelPlayerRecord],
    turns: list[TurnRecord] | None = None,
) -> RoundRecord:
    """Create a RoundRecord for testing."""
    round_record = RoundRecord(
        phase=phase,
        community_cards=(),
        player_records=player_records,
    )
    if turns:
        round_record.turns = turns
    return round_record


def make_hand_outcome(
    winner_ids: tuple[str, ...],
    pot_amount: int,
    was_showdown: bool = False,
    showdown_results: tuple[ShowdownResult, ...] = (),
    player_outcomes: tuple[PlayerOutcome, ...] | None = None,
    eliminated: tuple[EliminatedInfo, ...] = (),
) -> HandOutcomeDetails:
    chips_per_winner = (
        pot_amount // len(winner_ids) if winner_ids else pot_amount
    )

    if player_outcomes is None:
        player_outcomes = tuple(
            PlayerOutcome(
                player_id=winner_id,
                player_name=f"Player_{winner_id}",
                chips_won=ChipAmount(chips_per_winner),
                final_stack=ChipAmount(1000),
            )
            for winner_id in winner_ids
        )

    # Build winner name lookup from player_outcomes
    player_name_map = {po.player_id: po.player_name for po in player_outcomes}

    winners = tuple(
        WinnerInfo(
            player_id=winner_id,
            player_name=player_name_map.get(winner_id, f"Player_{winner_id}"),
            amount=ChipAmount(chips_per_winner),
        )
        for winner_id in winner_ids
    )

    return HandOutcomeDetails(
        winners=winners,
        eliminated=eliminated,
        showdown=(
            showdown_results if was_showdown and showdown_results else None
        ),
        pot_amount=ChipAmount(pot_amount),
        player_outcomes=player_outcomes,
    )


def make_showdown_result(
    player_id: str,
    player_name: str,
    hole_cards: Hand,
    hand_rank: HandRank = HandRank.PAIR,
) -> ShowdownResult:
    """Create a ShowdownResult for testing."""
    return ShowdownResult(
        player_id=player_id,
        player_name=player_name,
        hole_cards=hole_cards,
        hand_evaluation=HandEvaluation(
            rank=hand_rank,
            cards_used=(
                Card(Suit.HEARTS, Rank.ACE),
                Card(Suit.DIAMONDS, Rank.ACE),
                Card(Suit.CLUBS, Rank.KING),
                Card(Suit.SPADES, Rank.QUEEN),
                Card(Suit.HEARTS, Rank.JACK),
            ),
            kickers=(Rank.ACE, Rank.KING, Rank.QUEEN),
        ),
    )


def make_game_record(
    game_id: str,
    metadata: GameMetadata,
    completed_hands: list[HandRecord] | None = None,
) -> GameRecord:
    """Create a GameRecord for testing."""
    record = GameRecord(
        game_id=game_id,
        metadata=metadata,
    )
    if completed_hands:
        record.completed_hands = completed_hands
    return record


@pytest.fixture
def sample_hole_cards() -> Hand:
    return Hand(
        card1=Card(Suit.HEARTS, Rank.ACE),
        card2=Card(Suit.SPADES, Rank.KING),
    )


@pytest.fixture
def sample_hole_cards_2() -> Hand:
    return Hand(
        card1=Card(Suit.DIAMONDS, Rank.QUEEN),
        card2=Card(Suit.CLUBS, Rank.JACK),
    )
