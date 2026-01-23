from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from src.domain.models.blinds import BlindLevel

if TYPE_CHECKING:
    from src.config.tournament.config import PayoutStructure, TournamentConfig
from src.domain.models.card import Card
from src.domain.models.chips import ChipAmount
from src.domain.models.player import HandParticipationStatus, Player, PlayerId
from src.domain.models.players import Players
from src.domain.models.pot import PotState
from src.domain.models.seat import Seat

GameId = str


class GameStatus(Enum):
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

    @classmethod
    def get_betting_phases(cls) -> tuple[GamePhase, ...]:
        """Returns phases where betting occurs (excludes SHOWDOWN)."""
        return (
            cls.PRE_FLOP,
            cls.FLOP,
            cls.TURN,
            cls.RIVER,
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
    seed: int

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

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status.value,
            "seed": self.seed,
        }


@dataclass(slots=True)
class HandState:
    hand_number: int
    current_phase: GamePhase
    community_cards: list[Card]
    is_initial_hand_setup: bool = False

    def __post_init__(self) -> None:
        if self.hand_number < 1:
            raise ValueError(f"Hand number must be at least 1: {self.hand_number}")
        if len(self.community_cards) > 5:
            raise ValueError(
                f"Cannot have more than 5 community cards: {len(self.community_cards)}"
            )
        valid_card_counts = {0, 3, 4, 5}
        if len(self.community_cards) not in valid_card_counts:
            raise ValueError(
                f"Community card count must be one of {valid_card_counts}, got {len(self.community_cards)}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "hand_number": self.hand_number,
            "current_phase": self.current_phase.value,
            "community_cards": [card.to_dict() for card in self.community_cards],
        }


NO_POSITION_TO_ACT: int = -1


@dataclass(slots=True)
class BettingState:
    """State tracking for the current betting round."""

    last_raise_increment: ChipAmount
    position_to_act: int

    def __post_init__(self) -> None:
        if self.last_raise_increment.value < 0:
            raise ValueError(
                f"Last raise increment cannot be negative: {self.last_raise_increment.value}"
            )
        if self.position_to_act != NO_POSITION_TO_ACT and self.position_to_act < 0:
            raise ValueError(
                f"Position to act must be non-negative or {NO_POSITION_TO_ACT}: {self.position_to_act}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_raise_increment": self.last_raise_increment.value,
            "position_to_act": self.position_to_act,
        }


@dataclass(frozen=True, slots=True)
class BlindState:
    current_blind_level: BlindLevel


@dataclass(slots=True)
class HandOutcome:
    hand_number: int
    winners: list[tuple[PlayerId, ChipAmount]]

    def __post_init__(self) -> None:
        if self.hand_number < 1:
            raise ValueError(f"Hand number must be at least 1: {self.hand_number}")
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
    button_seat: Seat
    blind_state: BlindState
    players: Players
    outcome: HandOutcome | None

    def __post_init__(self) -> None:
        # Convert list[Player] to Players for backward compatibility
        if isinstance(self.players, list):
            object.__setattr__(self, "players", Players.from_list(self.players))

        num_players = len(self.players)
        if num_players < 2:
            raise ValueError(f"Game must have at least 2 players: {num_players}")
        if num_players > 6:
            raise ValueError(f"Game cannot have more than 6 players: {num_players}")

        valid_seats = {player.seat.value for player in self.players}
        if len(valid_seats) != num_players:
            raise ValueError("Player seats must be unique")
        if max(valid_seats) >= num_players:
            raise ValueError(
                f"Player seat {max(valid_seats)} is out of range for {num_players} players"
            )

        if self.button_seat.value < 0:
            raise ValueError(f"Button seat must be non-negative: {self.button_seat.value}")
        if self.button_seat.value >= num_players:
            raise ValueError(
                f"Button seat {self.button_seat.value} is out of range for {num_players} players"
            )

        if self.identity.status == GameStatus.IN_PROGRESS:
            if self.betting_state.position_to_act == NO_POSITION_TO_ACT:
                # Allow NO_POSITION_TO_ACT during initial setup (before first hand dealt)
                if not self.hand_state.is_initial_hand_setup and not self.is_round_complete():
                    raise ValueError(
                        "IN_PROGRESS game with NO_POSITION_TO_ACT must have a complete betting round"
                    )
            elif self.betting_state.position_to_act >= num_players:
                raise ValueError(
                    f"Position to act {self.betting_state.position_to_act} is out of range for {num_players} players"
                )

        if self.identity.status == GameStatus.COMPLETED:
            if self.outcome is None:
                raise ValueError("COMPLETED game must have outcome")
            if not self.outcome.winners:
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
    def position_to_act(self) -> int:
        return self.betting_state.position_to_act

    @property
    def buy_in_amount(self) -> ChipAmount:
        return self.tournament_config.buy_in_amount

    @property
    def payout_structure(self) -> PayoutStructure:
        return self.tournament_config.payout_structure

    def get_active_players(self) -> list[Player]:
        """Get list of all active (non-eliminated) players."""
        return [
            p for p in self.players if p.participation_status != HandParticipationStatus.ELIMINATED
        ]

    def get_active_player_ids(self) -> frozenset[PlayerId]:
        """Get set of IDs for all active (non-eliminated) players."""
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
        return self.players.get_by_seat(seat)

    def get_player_by_id(self, player_id: str) -> Player | None:
        return self.players.get_by_id(player_id)

    def is_hand_complete(self) -> bool:
        """
        Check if hand is complete.

        A hand is complete when:
        1. We've reached showdown phase
        2. Only one player remains (all others folded)
        """
        if self.current_phase == GamePhase.SHOWDOWN:
            return True

        return len(self.players_in_hand()) == 1

    def is_round_complete(self) -> bool:
        """
        Determine if current betting round is complete.

        Framework:
        1. SHOWDOWN has no betting → always complete
        2. If only 1 player remains (not folded) → hand ends → round complete
        3. If all players in hand have acted AND investments are equal → round complete
        4. If all players in hand are all-in → round complete (no more betting)
        5. Otherwise → round continues
        """
        if self.current_phase == GamePhase.SHOWDOWN:
            return True

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

    def get_player_to_act_id(self) -> PlayerId | None:
        """Get the ID of the player who needs to act.

        Returns:
            The player ID if there's a player who needs to act, None otherwise.
        """
        if self.status != GameStatus.IN_PROGRESS:
            return None

        if self.is_hand_complete():
            return None

        if self.position_to_act == NO_POSITION_TO_ACT:
            return None

        seat = Seat.from_int(self.position_to_act)
        player = self.get_player_by_seat(seat)

        if player is None:
            return None

        if not player.can_act():
            return None

        return player.id

    def is_tournament_complete(self) -> bool:
        """Check if the tournament is complete (only one player has chips remaining)."""
        return len(self.get_active_players()) == 1

    def get_winner(self) -> Player | None:
        """Get the tournament winner if the tournament is complete.

        Returns:
            The winning Player object if exactly one active player remains,
            None otherwise.
        """
        if not self.is_tournament_complete():
            return None

        active_players: list[Player] = self.get_active_players()
        if len(active_players) == 1:
            return active_players[0]

        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "hand_state": self.hand_state.to_dict(),
            "pot_state": self.pot_state.to_dict(),
            "betting_state": self.betting_state.to_dict(),
            "button_seat": self.button_seat.value,
            "blind_level": self.current_blind_level.to_dict(),
            "players": self.players.to_dict(),
            "player_to_act_id": self.get_player_to_act_id(),
        }
