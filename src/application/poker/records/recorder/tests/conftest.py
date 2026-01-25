"""Pytest fixtures for game recorder tests."""

from collections.abc import Callable
from datetime import datetime

import pytest

from src.application.poker.records.models import GameMetadata
from src.application.poker.records.recorder import Recorder
from src.config.blind_schedule.config import BlindSchedule, BlindScheduleEntry
from src.config.poker.config import PokerPlayerConfig
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
    GameStatus,
    HandOutcome,
    HandPhase,
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
STARTING_CHIPS = ChipAmount(1000)


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
        hole_cards: Hand | None = None,
        stack_at_hand_start: ChipAmount | None = None,
        can_raise: bool = True,
        name: str | None = None,
    ) -> Player:
        if total_invested_this_hand is None:
            total_invested_this_hand = ChipAmount(0)
        if name is None:
            name = f"Player {player_id}"

        return Player(
            id=player_id,
            name=name,
            bot_id=sample_bot.id,
            seat=seat,
            remaining_chips=remaining_chips,
            hole_cards=hole_cards,
            betting_status=betting_status,
            participation_status=participation_status,
            total_invested_this_hand=total_invested_this_hand,
            stack_at_hand_start=stack_at_hand_start,
            can_raise=can_raise,
        )

    return create_player


@pytest.fixture
def player_names() -> dict[str, str]:
    """Standard player names mapping."""
    return {
        "player-1": "Alice",
        "player-2": "Bob",
        "player-3": "Charlie",
        "player-4": "Diana",
        "player-5": "Eve",
        "player-6": "Frank",
    }


@pytest.fixture
def player_configs(
    player_names: dict[str, str]
) -> dict[str, PokerPlayerConfig]:
    """Create player configs from player names for game recorder tests."""
    return {
        player_id: PokerPlayerConfig(
            player_id=player_id,
            name=name,
            model_id=LlmModel.OPENAI_GPT4O_MINI,
        )
        for player_id, name in player_names.items()
    }


@pytest.fixture
def game_metadata() -> GameMetadata:
    """Standard game metadata for tests."""
    return GameMetadata(
        seed=42,
        buy_in_amount=ChipAmount(1000),
        starting_chip_stack=ChipAmount(1000),
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
        payout_structure=PayoutStructure.WINNER_TAKES_ALL,
        started_at=datetime.now(),
    )


@pytest.fixture
def tournament_config() -> TournamentConfig:
    """Standard tournament config for tests."""
    return TournamentConfig(
        buy_in_amount=ChipAmount(1000),
        starting_chip_stack=ChipAmount(1000),
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


def make_community_cards(phase: HandPhase) -> list[Card]:
    """Create community cards for testing based on phase.

    Returns the correct number of cards for each phase:
    - PRE_FLOP: 0 cards
    - FLOP: 3 cards
    - TURN: 4 cards
    - RIVER: 5 cards
    - SHOWDOWN: 5 cards
    """
    card_count = phase.card_count

    if card_count == 0:
        return []

    # Create cards based on required count
    all_cards = [
        Card(rank=Rank.ACE, suit=Suit.SPADES),
        Card(rank=Rank.KING, suit=Suit.HEARTS),
        Card(rank=Rank.QUEEN, suit=Suit.DIAMONDS),
        Card(rank=Rank.JACK, suit=Suit.CLUBS),
        Card(rank=Rank.TEN, suit=Suit.SPADES),
    ]

    return all_cards[:card_count]


def make_hole_cards(rank1: Rank = Rank.ACE, rank2: Rank = Rank.KING) -> Hand:
    """Create hole cards for testing."""
    return Hand(
        card1=Card(rank=rank1, suit=Suit.SPADES),
        card2=Card(rank=rank2, suit=Suit.HEARTS),
    )


@pytest.fixture
def game_factory(
    tournament_config: TournamentConfig,
) -> Callable[..., Game]:
    """Factory to create Game instances with configurable properties."""

    def create_game(
        players: list[Player],
        current_phase: HandPhase = HandPhase.PRE_FLOP,
        hand_number: int = 1,
        button_seat: Seat = Seat.SEAT_0,
        pot_amount: ChipAmount | None = None,
        outcome: HandOutcome | None = None,
        status: GameStatus = GameStatus.IN_PROGRESS,
    ) -> Game:
        if pot_amount is None:
            pot_amount = ChipAmount(0)
        now = datetime.now()

        # Create community cards based on phase (0 for PRE_FLOP, 5 for others)
        community_cards = make_community_cards(current_phase)

        return Game(
            identity=GameIdentity(
                id="test-game-1",
                created_at=now,
                updated_at=now,
                started_at=now,
                completed_at=now if status == GameStatus.COMPLETED else None,
                status=status,
                seed=42,
            ),
            tournament_config=tournament_config,
            hand_state=HandState(
                hand_number=hand_number,
                current_phase=current_phase,
                community_cards=community_cards,
                is_initial_hand_setup=True,
            ),
            pot_state=PotState(
                main_pot=Pot(
                    amount=pot_amount,
                    eligible_player_ids=frozenset({p.id for p in players}),
                ),
                side_pots=[],
            ),
            betting_state=BettingState(
                last_raise_increment=ChipAmount(0),
                position_to_act=0,
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
def recorder(player_configs: dict[str, PokerPlayerConfig]) -> Recorder:
    """Create a fresh Recorder instance."""
    return Recorder(player_configs=player_configs)


@pytest.fixture
def two_player_game(
    player_factory: Callable[..., Player],
    game_factory: Callable[..., Game],
) -> Game:
    """Create a basic 2-player game."""
    players = [
        player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=STARTING_CHIPS,
            hole_cards=make_hole_cards(Rank.ACE, Rank.KING),
            stack_at_hand_start=STARTING_CHIPS,
        ),
        player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=STARTING_CHIPS,
            hole_cards=make_hole_cards(Rank.QUEEN, Rank.JACK),
            stack_at_hand_start=STARTING_CHIPS,
        ),
    ]
    return game_factory(players=players)


@pytest.fixture
def three_player_game(
    player_factory: Callable[..., Player],
    game_factory: Callable[..., Game],
) -> Game:
    """Create a basic 3-player game."""
    players = [
        player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=STARTING_CHIPS,
            hole_cards=make_hole_cards(Rank.ACE, Rank.KING),
            stack_at_hand_start=STARTING_CHIPS,
        ),
        player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=STARTING_CHIPS,
            hole_cards=make_hole_cards(Rank.QUEEN, Rank.JACK),
            stack_at_hand_start=STARTING_CHIPS,
        ),
        player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=STARTING_CHIPS,
            hole_cards=make_hole_cards(Rank.TEN, Rank.NINE),
            stack_at_hand_start=STARTING_CHIPS,
        ),
    ]
    return game_factory(players=players)
