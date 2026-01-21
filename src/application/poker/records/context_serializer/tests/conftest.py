"""Fixtures for context serializer tests."""

from __future__ import annotations

from datetime import datetime

import pytest

from src.application.poker.records.models import (ActionRecord, GameMetadata,
                                                  GameRecord,
                                                  HandLevelPlayerRecord,
                                                  HandOutcome, HandRecord,
                                                  PlayerOutcome,
                                                  RoundLevelPlayerRecord,
                                                  RoundRecord, ShowdownResult,
                                                  TurnLevelPlayerRecord,
                                                  TurnRecord)
from src.config.blind_schedule.config import BlindSchedule, BlindScheduleEntry
from src.config.tournament.config import PayoutStructure
from src.domain.models.actions import ActionType
from src.domain.models.blinds import BlindLevel
from src.domain.models.card import Card, Rank, Suit
from src.domain.models.chips import ChipAmount
from src.domain.models.game import GamePhase
from src.domain.models.hand import Hand
from src.domain.models.llm_model import LlmModel
from src.domain.models.player import HandParticipationStatus
from src.domain.models.position import PositionName
from src.domain.models.seat import Seat
from src.domain.rules.hand_evaluator import HandEvaluation, HandRank


@pytest.fixture
def default_blind_level() -> BlindLevel:
    return BlindLevel(small_blind=ChipAmount(25), big_blind=ChipAmount(50), level=1)


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
def default_game_metadata(default_blind_schedule: BlindSchedule) -> GameMetadata:
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
        model_id=LlmModel.NONE,
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
        model_id=LlmModel.NONE,
        chips_at_round_start=ChipAmount(chips_at_round_start),
        total_invested_in_hand_at_round_start=ChipAmount(total_invested),
        participation_status=HandParticipationStatus.IN_HAND,
        is_all_in=False,
    )


def make_turn_level_player_record(
    player_id: str,
    player_name: str,
    seat: Seat,
    chips: int = 1000,
    total_invested: int = 0,
) -> TurnLevelPlayerRecord:
    """Create a TurnLevelPlayerRecord for testing."""
    return TurnLevelPlayerRecord(
        player_id=player_id,
        player_name=player_name,
        seat=seat,
        chips=ChipAmount(chips),
        model_id=LlmModel.NONE,
        total_invested_before_action=ChipAmount(total_invested),
        can_raise=True,
    )


def make_action_record(
    player_id: str,
    player_name: str,
    action_type: ActionType,
    amount: int | None = None,
    phase: GamePhase = GamePhase.PRE_FLOP,
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
    seat: Seat,
    action_type: ActionType,
    amount: int | None = None,
    phase: GamePhase = GamePhase.PRE_FLOP,
    turn_number: int = 1,
    pot_before: int = 0,
    pot_after: int = 0,
) -> TurnRecord:
    """Create a TurnRecord for testing."""
    return TurnRecord(
        round_turn_number=turn_number,
        player_record=make_turn_level_player_record(player_id, player_name, seat),
        action=make_action_record(player_id, player_name, action_type, amount, phase),
        timestamp=datetime.now(),
        pot_before=ChipAmount(pot_before),
        pot_after=ChipAmount(pot_after),
        current_bet_before=ChipAmount(0),
        current_bet_after=ChipAmount(amount or 0),
    )


def make_hand_record(
    hand_number: int,
    player_records: dict[str, HandLevelPlayerRecord],
    rounds: list[RoundRecord] | None = None,
    outcome: HandOutcome | None = None,
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
    phase: GamePhase,
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
) -> HandOutcome:
    """Create a HandOutcome for testing."""
    if player_outcomes is None:
        player_outcomes = tuple(
            PlayerOutcome(
                player_id=winner_id,
                player_name=f"Player_{winner_id}",
                chips_won=ChipAmount(pot_amount // len(winner_ids)),
                final_stack=ChipAmount(1000),
            )
            for winner_id in winner_ids
        )
    return HandOutcome(
        winner_ids=winner_ids,
        pot_amount=ChipAmount(pot_amount),
        was_showdown=was_showdown,
        showdown_results=showdown_results,
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
