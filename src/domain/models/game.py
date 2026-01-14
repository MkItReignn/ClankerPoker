from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.domain.models.blinds import BlindLevel, BlindSchedule
from src.domain.models.card import Card
from src.domain.models.chips import ChipAmount
from src.domain.models.player import HandParticipationStatus, Player, PlayerId
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

    @property
    def card_count(self) -> int:
        """Number of community cards required for this phase."""
        mapping = {
            GamePhase.PRE_FLOP: 0,
            GamePhase.FLOP: 3,
            GamePhase.TURN: 4,
            GamePhase.RIVER: 5,
            GamePhase.SHOWDOWN: 5,
        }
        return mapping[self]

    @classmethod
    def get_phase_order(cls) -> tuple[GamePhase, ...]:
        """Returns phases in sequence order."""
        return (
            cls.PRE_FLOP,
            cls.FLOP,
            cls.TURN,
            cls.RIVER,
            cls.SHOWDOWN,
        )

    def next_phase(self) -> GamePhase | None:
        """Returns the next phase in sequence, or None if this is the last phase."""
        order = self.get_phase_order()
        try:
            current_index = order.index(self)
            if current_index + 1 >= len(order):
                return None
            return order[current_index + 1]
        except ValueError:
            return None


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
    blind_schedule: BlindSchedule | None = None

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
        expected_cards = self.current_phase.card_count
        if len(self.community_cards) != expected_cards:
            raise ValueError(
                f"Phase {self.current_phase.value} requires {expected_cards} community cards, got {len(self.community_cards)}"
            )


NO_CURRENT_PLAYER: int = -1


@dataclass(slots=True)
class BettingState:
    """State tracking for the current betting round."""

    last_raise_increment: ChipAmount
    current_player_position: int

    def __post_init__(self) -> None:
        if self.last_raise_increment.value < 0:
            raise ValueError(
                f"Last raise increment cannot be negative: {self.last_raise_increment.value}"
            )
        if self.current_player_position != NO_CURRENT_PLAYER and self.current_player_position < 0:
            raise ValueError(
                f"Current player position must be non-negative or {NO_CURRENT_PLAYER}: {self.current_player_position}"
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
            if self.betting_state.current_player_position == NO_CURRENT_PLAYER:
                if not self.is_round_complete():
                    raise ValueError(
                        "IN_PROGRESS game with NO_CURRENT_PLAYER must have a complete betting round"
                    )
            elif self.betting_state.current_player_position >= len(self.players):
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
    def current_player_position(self) -> int:
        return self.betting_state.current_player_position

    @property
    def buy_in_amount(self) -> ChipAmount:
        return self.tournament_config.buy_in_amount

    @property
    def payout_structure(self) -> str:
        return self.tournament_config.payout_structure

    def get_non_eliminated_players(self) -> list[Player]:
        """Get list of all non-eliminated players."""
        return [
            p for p in self.players if p.participation_status != HandParticipationStatus.ELIMINATED
        ]

    def get_non_eliminated_player_ids(self) -> frozenset[PlayerId]:
        """Get set of IDs for all non-eliminated players."""
        return frozenset(
            p.id
            for p in self.players
            if p.participation_status != HandParticipationStatus.ELIMINATED
        )

    def players_in_hand(self, excluded_player_id: PlayerId | None = None) -> list[Player]:
        """Get all players currently in hand, optionally excluding a specific player."""
        players = [p for p in self.players if p.is_in_hand()]
        if excluded_player_id is not None:
            players = [p for p in players if p.id != excluded_player_id]
        return players

    def get_player_by_seat(self, seat: Seat) -> Player | None:
        return next((p for p in self.players if p.seat == seat), None)

    def get_player_by_id(self, player_id: str) -> Player | None:
        return next((p for p in self.players if p.id == player_id), None)

    def is_hand_complete(self) -> bool:
        """
        Check if hand is complete.

        A hand is complete when:
        1. We've reached showdown phase → betting complete, proceed to determine winners
        2. Only one player remains (all others folded) → early win, no showdown needed
        """
        if self.current_phase == GamePhase.SHOWDOWN:
            return True

        players_in_hand = [p for p in self.players if p.is_in_hand()]
        return len(players_in_hand) == 1

    def is_round_complete(self) -> bool:
        """
        Determine if current betting round is complete.

        Framework:
        1. If only 1 player remains (not folded) → hand ends → round complete
        2. If all players in hand have acted AND investments are equal → round complete
        3. If all players in hand are all-in → round complete (no more betting)
        4. Otherwise → round continues
        """
        from src.domain.rules.betting_calculator import BettingCalculator

        players_in_hand = self.players_in_hand()

        if len(players_in_hand) == 1:
            return True

        max_invested: ChipAmount = BettingCalculator.get_max_invested_this_hand(players_in_hand)
        for player in players_in_hand:
            if player.is_all_in():
                continue

            call_amount: ChipAmount = BettingCalculator.calculate_call_amount(
                max_invested, player.total_invested_this_hand
            )
            if call_amount.value > 0:
                return False

            if not player.has_acted_this_round():
                return False

        return True
