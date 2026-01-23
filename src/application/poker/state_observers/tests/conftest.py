from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

import pytest

from src.config.blind_schedule.config import BlindSchedule, BlindScheduleEntry
from src.config.tournament.config import PayoutStructure, TournamentConfig
from src.domain.models.blinds import BlindLevel
from src.domain.models.bot import Bot, BotId, BotType, Prompt
from src.domain.models.card import Card, Rank, Suit
from src.domain.models.chips import ChipAmount
from src.domain.models.game import (
    BettingState,
    BlindState,
    Game,
    GameIdentity,
    GamePhase,
    GameStatus,
    HandOutcome,
    HandState,
)
from src.domain.models.hand import Hand
from src.domain.models.llm_model import LlmModel
from src.domain.models.player import (
    BettingRoundActionStatus,
    HandParticipationStatus,
    Player,
    PlayerId,
)
from src.domain.models.players import Players
from src.domain.models.pot import Pot, PotState
from src.domain.models.seat import Seat

SMALL_BLIND = ChipAmount(10)
BIG_BLIND = ChipAmount(20)
STARTING_STACK = ChipAmount(1000)


@pytest.fixture
def sample_bot() -> Bot:
    return Bot(
        id=BotId("test-bot"),
        name="Test Bot",
        bot_type=BotType.HOUSE,
        llm_model=LlmModel.OPENAI_GPT4O_MINI,
        system_prompt=Prompt("Test prompt"),
    )


@pytest.fixture
def sample_player_factory(sample_bot: Bot) -> Callable[..., Player]:
    def create_player(
        player_id: PlayerId,
        seat: Seat,
        remaining_chips: ChipAmount,
        total_invested_this_hand: ChipAmount | None = None,
        participation_status: HandParticipationStatus | None = None,
        betting_status: BettingRoundActionStatus | None = None,
        hole_cards: Hand | None = None,
        name: str | None = None,
        elimination_hand_number: int | None = None,
        table_finish_position: int | None = None,
    ) -> Player:
        return Player(
            id=player_id,
            name=name or f"Player {player_id}",
            bot_id=sample_bot.id,
            seat=seat,
            remaining_chips=remaining_chips,
            hole_cards=hole_cards,
            betting_status=betting_status or BettingRoundActionStatus.NEEDS_ACTION,
            participation_status=participation_status or HandParticipationStatus.IN_HAND,
            total_invested_this_hand=total_invested_this_hand or ChipAmount(0),
            elimination_hand_number=elimination_hand_number,
            table_finish_position=table_finish_position,
        )

    return create_player


def _create_community_cards_for_phase(phase: GamePhase) -> list[Card]:
    required_count = phase.card_count
    cards = []
    ranks = [Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK, Rank.TEN]
    suits = [Suit.SPADES, Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS, Suit.SPADES]
    for i in range(required_count):
        cards.append(Card(rank=ranks[i], suit=suits[i]))
    return cards


@pytest.fixture
def game_factory() -> Callable[..., Game]:
    def create_game(
        players: list[Player],
        current_phase: GamePhase = GamePhase.PRE_FLOP,
        button_seat: Seat = Seat.SEAT_0,
        hand_number: int = 1,
        outcome: HandOutcome | None = None,
        status: GameStatus = GameStatus.IN_PROGRESS,
        community_cards: list[Card] | None = None,
        position_to_act: int = 0,
    ) -> Game:
        now = datetime.now()
        if community_cards is None:
            community_cards = _create_community_cards_for_phase(current_phase)
        return Game(
            identity=GameIdentity(
                id="test-game",
                created_at=now,
                updated_at=now,
                started_at=now,
                completed_at=now if status == GameStatus.COMPLETED else None,
                status=status,
                seed=42,
            ),
            tournament_config=TournamentConfig(
                buy_in_amount=STARTING_STACK,
                starting_chip_stack=STARTING_STACK,
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
            ),
            hand_state=HandState(
                hand_number=hand_number,
                current_phase=current_phase,
                community_cards=community_cards,
                is_initial_hand_setup=False,
            ),
            pot_state=PotState(
                main_pot=Pot(
                    amount=ChipAmount(0),
                    eligible_player_ids=frozenset(p.id for p in players),
                ),
                side_pots=[],
            ),
            betting_state=BettingState(
                last_raise_increment=ChipAmount(0),
                position_to_act=position_to_act,
            ),
            button_seat=button_seat,
            blind_state=BlindState(
                current_blind_level=BlindLevel(
                    small_blind=SMALL_BLIND,
                    big_blind=BIG_BLIND,
                    level=1,
                )
            ),
            players=Players.from_list(players),
            outcome=outcome,
        )

    return create_game


@pytest.fixture
def sample_hand() -> Hand:
    return Hand(
        card1=Card(rank=Rank.ACE, suit=Suit.SPADES),
        card2=Card(rank=Rank.KING, suit=Suit.SPADES),
    )


@pytest.fixture
def another_hand() -> Hand:
    return Hand(
        card1=Card(rank=Rank.QUEEN, suit=Suit.HEARTS),
        card2=Card(rank=Rank.JACK, suit=Suit.HEARTS),
    )
