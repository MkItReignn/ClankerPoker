from __future__ import annotations

from typing import TypeAlias

from src.domain.models.game import NO_POSITION_TO_ACT, GamePhase
from src.domain.models.player import HandParticipationStatus, Player
from src.domain.models.players import Players
from src.domain.models.position import PositionName, TablePositionMapping
from src.domain.models.seat import Seat

is_heads_up: TypeAlias = bool


class PositionManager:
    """Centralized position management for poker game.

    Handles ALL position-related logic:
    - Button advancement
    - Blind position calculation
    - Position mapping creation
    - Betting order determination
    """

    BETTING_ORDER_RULES: dict[tuple[GamePhase, is_heads_up], list[PositionName]] = {
        (GamePhase.PRE_FLOP, True): [
            PositionName.SMALL_BLIND,
            PositionName.BIG_BLIND,
        ],
        (GamePhase.PRE_FLOP, False): [
            PositionName.UNDER_THE_GUN,
            PositionName.UTG_PLUS_ONE,
            PositionName.CUTOFF,
            PositionName.BUTTON,
            PositionName.SMALL_BLIND,
            PositionName.BIG_BLIND,
        ],
        (GamePhase.FLOP, True): [
            PositionName.BIG_BLIND,
            PositionName.SMALL_BLIND,
        ],
        (GamePhase.TURN, True): [
            PositionName.BIG_BLIND,
            PositionName.SMALL_BLIND,
        ],
        (GamePhase.RIVER, True): [
            PositionName.BIG_BLIND,
            PositionName.SMALL_BLIND,
        ],
        (GamePhase.FLOP, False): [
            PositionName.SMALL_BLIND,
            PositionName.BIG_BLIND,
            PositionName.UNDER_THE_GUN,
            PositionName.UTG_PLUS_ONE,
            PositionName.CUTOFF,
            PositionName.BUTTON,
        ],
        (GamePhase.TURN, False): [
            PositionName.SMALL_BLIND,
            PositionName.BIG_BLIND,
            PositionName.UNDER_THE_GUN,
            PositionName.UTG_PLUS_ONE,
            PositionName.CUTOFF,
            PositionName.BUTTON,
        ],
        (GamePhase.RIVER, False): [
            PositionName.SMALL_BLIND,
            PositionName.BIG_BLIND,
            PositionName.UNDER_THE_GUN,
            PositionName.UTG_PLUS_ONE,
            PositionName.CUTOFF,
            PositionName.BUTTON,
        ],
    }

    @staticmethod
    def resolve_positions_for_new_hand(
        all_players: list[Player],
        previous_button_seat: Seat,
        is_initial_hand_setup: bool = False,
    ) -> TablePositionMapping:
        """Resolve all positions for a new hand.

        Computes complete position mapping including:
        - Button seat (advanced if not initial hand setup)
        - Small blind seat
        - Big blind seat
        - Heads-up status
        - Total seats at table

        Returns:
            Complete position mapping for the new hand.
        """
        if len(all_players) < 2:
            raise ValueError(f"Need at least 2 players, got {len(all_players)}")

        active_count = sum(
            1 for p in all_players if p.participation_status != HandParticipationStatus.ELIMINATED
        )
        if active_count < 2:
            raise ValueError(f"Need at least 2 active players, got {active_count}")

        if is_initial_hand_setup:
            button_seat = previous_button_seat
        else:
            button_seat = PositionManager.advance_button(
                all_players=all_players,
                current_button_seat=previous_button_seat,
            )

        small_blind_seat, big_blind_seat = PositionManager._calculate_blind_positions(
            all_players, button_seat
        )

        is_heads_up = active_count == 2

        utg_seat, utg_plus_one_seat, cutoff_seat = PositionManager._calculate_relative_positions(
            all_players=all_players,
            button_seat=button_seat,
            big_blind_seat=big_blind_seat,
            active_count=active_count,
        )

        return TablePositionMapping(
            button_seat=button_seat,
            small_blind_seat=small_blind_seat,
            big_blind_seat=big_blind_seat,
            utg_seat=utg_seat,
            utg_plus_one_seat=utg_plus_one_seat,
            cutoff_seat=cutoff_seat,
            is_heads_up=is_heads_up,
            active_players_count=active_count,
            total_seats_at_table=len(all_players),
        )

    @staticmethod
    def advance_button(
        all_players: list[Player],
        current_button_seat: Seat,
    ) -> Seat:
        """Advance button to next active player.

        Button moves clockwise, skipping eliminated players.
        """
        total_seats = len(all_players)
        return PositionManager._find_next_active_seat(all_players, current_button_seat, total_seats)

    @staticmethod
    def _calculate_blind_positions(
        all_players: list[Player], button_seat: Seat
    ) -> tuple[Seat, Seat]:
        """Calculate small blind and big blind positions from button.

        Rules:
        - Heads-up: Button = Small Blind, other player = Big Blind
        - Normal play: SB is left of button, BB is left of SB
        """
        total_seats = len(all_players)
        active_count = sum(
            1 for p in all_players if p.participation_status != HandParticipationStatus.ELIMINATED
        )

        is_heads_up = active_count == 2

        if is_heads_up:
            small_blind_seat = button_seat
            big_blind_seat = PositionManager._find_next_active_seat(
                all_players, button_seat, total_seats
            )
        else:
            small_blind_seat = PositionManager._find_next_active_seat(
                all_players, button_seat, total_seats
            )
            big_blind_seat = PositionManager._find_next_active_seat(
                all_players, small_blind_seat, total_seats
            )

        return (small_blind_seat, big_blind_seat)

    @staticmethod
    def _find_next_active_seat(
        all_players: list[Player], start_seat: Seat, total_seats: int
    ) -> Seat:
        """Find next active (non-eliminated) seat clockwise from start_seat.

        Skips eliminated players. Wraps around if needed.
        """
        start_seat_int = start_seat.value
        next_seat_int = (start_seat_int + 1) % total_seats
        for _ in range(total_seats):
            if (
                all_players[next_seat_int].participation_status
                != HandParticipationStatus.ELIMINATED
            ):
                return Seat.from_int(next_seat_int)
            next_seat_int = (next_seat_int + 1) % total_seats
        return start_seat

    @staticmethod
    def _find_previous_active_seat(
        all_players: list[Player], start_seat: Seat, total_seats: int
    ) -> Seat:
        """Find previous active (non-eliminated) seat counter-clockwise from start_seat.

        Skips eliminated players. Wraps around if needed.
        Used for Cutoff position (right of button).
        """
        start_seat_int = start_seat.value
        prev_seat_int = (start_seat_int - 1) % total_seats
        for _ in range(total_seats):
            if (
                all_players[prev_seat_int].participation_status
                != HandParticipationStatus.ELIMINATED
            ):
                return Seat.from_int(prev_seat_int)
            prev_seat_int = (prev_seat_int - 1) % total_seats
        return start_seat

    @staticmethod
    def _calculate_relative_positions(
        all_players: list[Player],
        button_seat: Seat,
        big_blind_seat: Seat,
        active_count: int,
    ) -> tuple[Seat | None, Seat | None, Seat | None]:
        """Calculate UTG, UTG+1, and Cutoff positions.

        Position mapping by active player count:
        - 2 players (heads-up): None, None, None
        - 3 players: None, None, None
        - 4 players: UTG, None, None
        - 5 players: UTG, None, CO
        - 6 players: UTG, UTG+1, CO

        Returns:
            Tuple of (utg_seat, utg_plus_one_seat, cutoff_seat)
            None values indicate position doesn't exist for this player count.
        """
        total_seats = len(all_players)

        if active_count <= 3:
            return (None, None, None)

        utg_seat = PositionManager._find_next_active_seat(all_players, big_blind_seat, total_seats)

        if active_count == 4:
            return (utg_seat, None, None)

        if active_count == 5:
            cutoff_seat = PositionManager._find_previous_active_seat(
                all_players, button_seat, total_seats
            )
            return (utg_seat, None, cutoff_seat)

        if active_count == 6:
            utg_plus_one_seat = PositionManager._find_next_active_seat(
                all_players, utg_seat, total_seats
            )

            cutoff_seat = PositionManager._find_previous_active_seat(
                all_players, button_seat, total_seats
            )

            return (utg_seat, utg_plus_one_seat, cutoff_seat)

        raise ValueError(f"Unexpected active player count: {active_count}. Expected 2-6 players.")

    @staticmethod
    def get_betting_order(
        position_mapping: TablePositionMapping,
        phase: GamePhase,
        players_in_hand: list[Player],
    ) -> list[Seat]:
        """Get betting order as list of seats.

        Rules:
        1. Get position order from BETTING_ORDER_RULES
        2. Map positions to seats
        3. Filter to only players in hand
        4. Return seats in betting order
        """
        is_heads_up = position_mapping.is_heads_up
        position_order = PositionManager.BETTING_ORDER_RULES.get((phase, is_heads_up))

        if position_order is None:
            raise ValueError(f"No betting order rule for phase={phase}, is_heads_up={is_heads_up}")

        seats_in_hand = {p.seat for p in players_in_hand}
        seat_order: list[Seat] = []

        for position_name in position_order:
            seat: Seat | None = position_mapping.get_seat_for_position(position_name)
            if seat is None:
                continue

            if seat in seat_order:
                continue

            if seat in seats_in_hand:
                seat_order.append(seat)

        return seat_order

    @staticmethod
    def find_first_position_to_act(
        betting_order: list[Seat],
        players: Players,
    ) -> int:
        """Find first position to act from betting order.

        Returns the seat value of the first player in betting order
        who is not all-in, or NO_POSITION_TO_ACT if all players are all-in.
        """
        for seat in betting_order:
            player: Player | None = players.get_by_seat(seat)
            if player and not player.is_all_in():
                return seat.value
        return NO_POSITION_TO_ACT
