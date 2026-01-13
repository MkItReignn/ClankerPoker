from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.domain.models.blinds import BlindLevel
from src.domain.models.card import Card
from src.domain.models.chips import ChipAmount
from src.domain.models.player import Player, PlayerId
from src.domain.models.pot import PotState
from src.domain.models.seat import Seat

GameId = str


class GameStatus(Enum):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class GamePhase(Enum):
    PRE_FLOP = "pre_flop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"


PHASE_CARD_COUNTS: dict[GamePhase, int] = {
    GamePhase.PRE_FLOP: 0,
    GamePhase.FLOP: 3,
    GamePhase.TURN: 4,
    GamePhase.RIVER: 5,
    GamePhase.SHOWDOWN: 5,
}


@dataclass(frozen=True, slots=True)
class GameIdentity:
    id: GameId
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    status: GameStatus

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Game id cannot be empty")
        if self.status == GameStatus.IN_PROGRESS and self.started_at is None:
            raise ValueError("IN_PROGRESS game must have started_at")
        if self.status == GameStatus.COMPLETED and self.completed_at is None:
            raise ValueError("COMPLETED game must have completed_at")
        if self.started_at is not None and self.started_at < self.created_at:
            raise ValueError("started_at cannot be before created_at")
        if self.completed_at is not None:
            if self.started_at is None:
                raise ValueError("completed_at requires started_at")
            if self.completed_at < self.started_at:
                raise ValueError("completed_at cannot be before started_at")


@dataclass(frozen=True, slots=True)
class TournamentConfig:
    buy_in_amount: ChipAmount
    starting_chip_stack: ChipAmount
    total_prize_pool: ChipAmount
    payout_structure: str

    def __post_init__(self) -> None:
        if self.buy_in_amount.value <= 0:
            raise ValueError(f"Buy-in must be positive: {self.buy_in_amount.value}")
        if self.starting_chip_stack.value <= 0:
            raise ValueError(
                f"Starting chip stack must be positive: {self.starting_chip_stack.value}"
            )
        if self.total_prize_pool.value < 0:
            raise ValueError(f"Total prize pool cannot be negative: {self.total_prize_pool.value}")


@dataclass(slots=True)
class HandState:
    hand_number: int
    current_phase: GamePhase
    community_cards: list[Card]

    def __post_init__(self) -> None:
        if self.hand_number < 1:
            raise ValueError(f"Hand number must be at least 1: {self.hand_number}")
        if len(self.community_cards) > 5:
            raise ValueError(
                f"Cannot have more than 5 community cards: {len(self.community_cards)}"
            )
        expected_cards = PHASE_CARD_COUNTS.get(self.current_phase, 0)
        if len(self.community_cards) != expected_cards:
            raise ValueError(
                f"Phase {self.current_phase.value} requires {expected_cards} community cards, got {len(self.community_cards)}"
            )


@dataclass(slots=True)
class BettingState:
    minimum_raise_amount: ChipAmount
    last_raise_amount: ChipAmount
    current_player_position: int | None

    def __post_init__(self) -> None:
        if self.minimum_raise_amount.value < 0:
            raise ValueError(
                f"Minimum raise amount cannot be negative: {self.minimum_raise_amount.value}"
            )
        if self.last_raise_amount.value < 0:
            raise ValueError(
                f"Last raise amount cannot be negative: {self.last_raise_amount.value}"
            )
        if self.current_player_position is not None and self.current_player_position < 0:
            raise ValueError(
                f"Current player position must be non-negative: {self.current_player_position}"
            )


@dataclass(slots=True)
class TablePositions:
    dealer_position: int
    small_blind_position: int
    big_blind_position: int

    def __post_init__(self) -> None:
        if self.dealer_position < 0:
            raise ValueError(f"Dealer position must be non-negative: {self.dealer_position}")
        if self.small_blind_position < 0:
            raise ValueError(
                f"Small blind position must be non-negative: {self.small_blind_position}"
            )
        if self.big_blind_position < 0:
            raise ValueError(f"Big blind position must be non-negative: {self.big_blind_position}")


@dataclass(frozen=True, slots=True)
class BlindState:
    current_blind_level: BlindLevel


@dataclass(slots=True)
class GameResults:
    winners: list[tuple[PlayerId, ChipAmount]]

    def __post_init__(self) -> None:
        if not self.winners:
            return
        total_payout = sum(payout.value for _, payout in self.winners)
        if total_payout < 0:
            raise ValueError(f"Total payout cannot be negative: {total_payout}")


@dataclass(slots=True)
class Game:
    identity: GameIdentity
    tournament_config: TournamentConfig
    hand_state: HandState
    pot_state: PotState
    betting_state: BettingState
    table_positions: TablePositions
    blind_state: BlindState
    players: list[Player]
    results: GameResults | None

    def __post_init__(self) -> None:
        if len(self.players) < 2:
            raise ValueError(f"Game must have at least 2 players: {len(self.players)}")
        if len(self.players) > 6:
            raise ValueError(f"Game cannot have more than 6 players: {len(self.players)}")

        valid_seats = {player.seat.value for player in self.players}
        if len(valid_seats) != len(self.players):
            raise ValueError("Player seats must be unique")
        if max(valid_seats) >= len(self.players):
            raise ValueError(
                f"Player seat {max(valid_seats)} is out of range for {len(self.players)} players"
            )

        if self.identity.status == GameStatus.IN_PROGRESS:
            if self.betting_state.current_player_position is None:
                raise ValueError("IN_PROGRESS game must have a current_player_position")
            if self.betting_state.current_player_position >= len(self.players):
                raise ValueError(
                    f"Current player position {self.betting_state.current_player_position} is out of range for {len(self.players)} players"
                )

        if self.identity.status == GameStatus.COMPLETED:
            if self.results is None:
                raise ValueError("COMPLETED game must have results")
            if not self.results.winners:
                raise ValueError("COMPLETED game must have at least one winner")

    @property
    def id(self) -> GameId:
        return self.identity.id

    @property
    def status(self) -> GameStatus:
        return self.identity.status

    @property
    def pot(self) -> ChipAmount:
        return self.pot_state.main_pot.amount

    @property
    def current_phase(self) -> GamePhase:
        return self.hand_state.current_phase

    @property
    def community_cards(self) -> list[Card]:
        return self.hand_state.community_cards

    @property
    def current_blind_level(self) -> BlindLevel:
        return self.blind_state.current_blind_level

    @property
    def dealer_position(self) -> int:
        return self.table_positions.dealer_position

    @property
    def small_blind_position(self) -> int:
        return self.table_positions.small_blind_position

    @property
    def big_blind_position(self) -> int:
        return self.table_positions.big_blind_position

    @property
    def current_player_position(self) -> int | None:
        return self.betting_state.current_player_position

    @property
    def buy_in_amount(self) -> ChipAmount:
        return self.tournament_config.buy_in_amount

    @property
    def payout_structure(self) -> str:
        return self.tournament_config.payout_structure

    def get_active_players(self) -> list[Player]:
        return [p for p in self.players if p.is_in_hand()]

    def get_player_by_seat(self, seat: Seat) -> Player | None:
        return next((p for p in self.players if p.seat == seat), None)

    def get_player_by_id(self, player_id: str) -> Player | None:
        return next((p for p in self.players if p.id == player_id), None)
