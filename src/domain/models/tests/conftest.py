"""Pytest fixtures for domain models tests."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import pytest

from src.domain.models.blinds import BlindLevel
from src.domain.models.bot import Bot, BotId, BotType, Prompt
from src.domain.models.card import Card, Rank, Suit
from src.domain.models.chips import ChipAmount
from src.domain.models.game import (BettingState, BlindState, Game,
                                    GameIdentity, GamePhase, GameStatus,
                                    HandState, TournamentConfig)
from src.domain.models.hand import Hand
from src.domain.models.llm_model import LlmModel
from src.domain.models.player import (BettingRoundActionStatus,
                                      HandParticipationStatus, Player,
                                      PlayerId)
from src.domain.models.pot import Pot, PotState
from src.domain.models.seat import Seat

ZERO_CHIPS = ChipAmount(0)
SMALL_BLIND_STANDARD = ChipAmount(10)
BIG_BLIND_STANDARD = ChipAmount(20)
MEDIUM_CHIPS = ChipAmount(50)
LARGE_CHIPS = ChipAmount(100)


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
def sample_player_factory(sample_bot: Bot) -> Callable[..., Player]:
    """Factory function to create players with configurable properties."""

    def create_player(
        player_id: PlayerId,
        seat: Seat,
        remaining_chips: ChipAmount,
        total_invested_this_hand: ChipAmount | None = None,
        participation_status: HandParticipationStatus | None = None,
        betting_status: BettingRoundActionStatus | None = None,
        hole_cards: Hand | None = None,
    ) -> Player:
        if total_invested_this_hand is None:
            total_invested_this_hand = ChipAmount(0)
        if participation_status is None:
            participation_status = HandParticipationStatus.IN_HAND
        if betting_status is None:
            betting_status = BettingRoundActionStatus.NEEDS_ACTION

        return Player(
            id=player_id,
            bot_id=sample_bot.id,
            seat=seat,
            remaining_chips=remaining_chips,
            hole_cards=hole_cards,
            betting_status=betting_status,
            participation_status=participation_status,
            total_invested_this_hand=total_invested_this_hand,
        )

    return create_player


def _create_community_cards_for_phase(phase: GamePhase) -> list[Card]:
    """Create the required number of community cards for a given phase."""
    required_count = phase.card_count
    cards = []
    ranks = [Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK, Rank.TEN]
    suits = [Suit.SPADES, Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS]
    for i in range(required_count):
        rank = ranks[i % len(ranks)]
        suit = suits[i % len(suits)]
        cards.append(Card(rank=rank, suit=suit))
    return cards


@pytest.fixture
def minimal_game_factory() -> Callable[..., Game]:
    """Factory to create minimal Game instances for testing."""

    def create_game(
        players: list[Player],
        current_phase: GamePhase | None = None,
        last_raise_increment: ChipAmount | None = None,
    ) -> Game:
        if last_raise_increment is None:
            last_raise_increment = ChipAmount(0)
        if current_phase is None:
            current_phase = GamePhase.PRE_FLOP
        now = datetime.now()
        community_cards = _create_community_cards_for_phase(current_phase)
        return Game(
            identity=GameIdentity(
                id="test-game-1",
                created_at=now,
                updated_at=now,
                started_at=now,
                completed_at=None,
                status=GameStatus.IN_PROGRESS,
            ),
            tournament_config=TournamentConfig(
                buy_in_amount=ChipAmount(1000),
                starting_chip_stack=ChipAmount(1000),
                total_prize_pool=ChipAmount(6000),
                payout_structure="standard",
            ),
            hand_state=HandState(
                hand_number=1,
                current_phase=current_phase,
                community_cards=community_cards,
            ),
            pot_state=PotState(
                main_pot=Pot(
                    amount=ChipAmount(0),
                    eligible_player_ids=frozenset({p.id for p in players}),
                ),
                side_pots=[],
            ),
            betting_state=BettingState(
                last_raise_increment=last_raise_increment,
                current_player_position=0,
            ),
            button_seat=Seat.SEAT_0,
            blind_state=BlindState(
                current_blind_level=BlindLevel(
                    small_blind=ChipAmount(10),
                    big_blind=ChipAmount(20),
                    level=1,
                )
            ),
            players=players,
            results=None,
        )

    return create_game
