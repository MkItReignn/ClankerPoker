"""Behavioral tests for PositionManager and TablePositionMapping.

Tests verify position system behavior according to RULE_BOOK.md:
- Button position tracking and rotation
- Blind positions (SB, BB) calculation
- Action order calculation (preflop vs postflop)
- Heads-up special rules (button is SB, acts first preflop)
- Correctly skipping eliminated players
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

import pytest

from src.domain.models.chips import ChipAmount
from src.domain.models.game import HandPhase
from src.domain.models.player import HandParticipationStatus, Player
from src.domain.models.position import PositionName, TablePositionMapping
from src.domain.models.seat import Seat
from src.domain.rules.position_manager import PositionManager


class TestPositionAssignmentTwoPlayers:
    """Heads-up (2 players): Button is also Small Blind, other player is Big Blind."""

    def test_button_is_small_blind_in_heads_up(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        assert mapping.button_seat == mapping.small_blind_seat
        assert mapping.is_heads_up is True

    def test_big_blind_is_non_button_player_in_heads_up(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        assert mapping.big_blind_seat == Seat.SEAT_1
        assert mapping.big_blind_seat != mapping.button_seat

    def test_heads_up_has_no_utg_or_cutoff_positions(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        assert mapping.utg_seat is None
        assert mapping.utg_plus_one_seat is None
        assert mapping.cutoff_seat is None


class TestPositionAssignmentThreePlayers:
    """Three players: BTN, SB, BB - no UTG/UTG+1/Cutoff positions."""

    def test_three_players_have_btn_sb_bb(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        assert mapping.button_seat == Seat.SEAT_0
        assert mapping.small_blind_seat == Seat.SEAT_1
        assert mapping.big_blind_seat == Seat.SEAT_2

    def test_three_players_have_no_utg_or_cutoff(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        assert mapping.utg_seat is None
        assert mapping.utg_plus_one_seat is None
        assert mapping.cutoff_seat is None
        assert mapping.is_heads_up is False

    def test_three_players_btn_and_sb_are_distinct(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        assert mapping.button_seat != mapping.small_blind_seat


class TestPositionAssignmentFourPlayers:
    """Four players: BTN, SB, BB, UTG."""

    def test_four_players_have_utg_position(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p4",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        assert mapping.button_seat == Seat.SEAT_0
        assert mapping.small_blind_seat == Seat.SEAT_1
        assert mapping.big_blind_seat == Seat.SEAT_2
        assert mapping.utg_seat == Seat.SEAT_3

    def test_four_players_have_no_utg_plus_one_or_cutoff(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p4",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        assert mapping.utg_plus_one_seat is None
        assert mapping.cutoff_seat is None


class TestPositionAssignmentFivePlayers:
    """Five players: BTN, SB, BB, UTG, CO."""

    def test_five_players_have_utg_and_cutoff(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p4",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p5",
                seat=Seat.SEAT_4,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        assert mapping.button_seat == Seat.SEAT_0
        assert mapping.small_blind_seat == Seat.SEAT_1
        assert mapping.big_blind_seat == Seat.SEAT_2
        assert mapping.utg_seat == Seat.SEAT_3
        assert mapping.cutoff_seat == Seat.SEAT_4

    def test_five_players_have_no_utg_plus_one(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p4",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p5",
                seat=Seat.SEAT_4,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        assert mapping.utg_plus_one_seat is None

    def test_cutoff_is_right_of_button(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p4",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p5",
                seat=Seat.SEAT_4,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        # Cutoff is previous seat from button (counter-clockwise)
        assert mapping.cutoff_seat == Seat.SEAT_4


class TestPositionAssignmentSixPlayers:
    """Six players: BTN, SB, BB, UTG, UTG+1, CO - full table."""

    def test_six_players_have_all_positions(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p4",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p5",
                seat=Seat.SEAT_4,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p6",
                seat=Seat.SEAT_5,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        assert mapping.button_seat == Seat.SEAT_0
        assert mapping.small_blind_seat == Seat.SEAT_1
        assert mapping.big_blind_seat == Seat.SEAT_2
        assert mapping.utg_seat == Seat.SEAT_3
        assert mapping.utg_plus_one_seat == Seat.SEAT_4
        assert mapping.cutoff_seat == Seat.SEAT_5

    def test_six_players_positions_wrap_around_table(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p4",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p5",
                seat=Seat.SEAT_4,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p6",
                seat=Seat.SEAT_5,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_4,
            advance_button=False,
        )

        assert mapping.button_seat == Seat.SEAT_4
        assert mapping.small_blind_seat == Seat.SEAT_5
        assert mapping.big_blind_seat == Seat.SEAT_0
        assert mapping.utg_seat == Seat.SEAT_1
        assert mapping.utg_plus_one_seat == Seat.SEAT_2
        assert mapping.cutoff_seat == Seat.SEAT_3


class TestActionOrderPreflop:
    """Preflop action order: UTG → ... → BTN → SB → BB (BB acts last)."""

    def test_preflop_order_utg_acts_first_in_six_player_game(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="btn",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="sb",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="bb",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="utg",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="utg1",
                seat=Seat.SEAT_4,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="co",
                seat=Seat.SEAT_5,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        betting_order = PositionManager.get_betting_order(
            position_mapping=mapping,
            phase=HandPhase.PRE_FLOP,
            players_in_hand=players,
        )

        assert betting_order[0] == Seat.SEAT_3  # UTG acts first

    def test_preflop_order_bb_acts_last_in_six_player_game(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="btn",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="sb",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="bb",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="utg",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="utg1",
                seat=Seat.SEAT_4,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="co",
                seat=Seat.SEAT_5,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        betting_order = PositionManager.get_betting_order(
            position_mapping=mapping,
            phase=HandPhase.PRE_FLOP,
            players_in_hand=players,
        )

        assert betting_order[-1] == Seat.SEAT_2  # BB acts last

    def test_preflop_order_is_utg_utg1_co_btn_sb_bb(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="btn",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="sb",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="bb",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="utg",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="utg1",
                seat=Seat.SEAT_4,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="co",
                seat=Seat.SEAT_5,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        betting_order = PositionManager.get_betting_order(
            position_mapping=mapping,
            phase=HandPhase.PRE_FLOP,
            players_in_hand=players,
        )

        expected_order = [
            Seat.SEAT_3,  # UTG
            Seat.SEAT_4,  # UTG+1
            Seat.SEAT_5,  # CO
            Seat.SEAT_0,  # BTN
            Seat.SEAT_1,  # SB
            Seat.SEAT_2,  # BB
        ]
        assert betting_order == expected_order


class TestActionOrderPostflop:
    """Postflop action order: SB → BB → ... → BTN (Button acts last)."""

    def test_postflop_order_sb_acts_first_in_six_player_game(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="btn",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="sb",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="bb",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="utg",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="utg1",
                seat=Seat.SEAT_4,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="co",
                seat=Seat.SEAT_5,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        betting_order = PositionManager.get_betting_order(
            position_mapping=mapping,
            phase=HandPhase.FLOP,
            players_in_hand=players,
        )

        assert betting_order[0] == Seat.SEAT_1  # SB acts first postflop

    def test_postflop_order_btn_acts_last_in_six_player_game(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="btn",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="sb",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="bb",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="utg",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="utg1",
                seat=Seat.SEAT_4,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="co",
                seat=Seat.SEAT_5,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        betting_order = PositionManager.get_betting_order(
            position_mapping=mapping,
            phase=HandPhase.FLOP,
            players_in_hand=players,
        )

        assert betting_order[-1] == Seat.SEAT_0  # BTN acts last postflop

    def test_postflop_order_is_sb_bb_utg_utg1_co_btn(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="btn",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="sb",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="bb",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="utg",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="utg1",
                seat=Seat.SEAT_4,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="co",
                seat=Seat.SEAT_5,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        betting_order = PositionManager.get_betting_order(
            position_mapping=mapping,
            phase=HandPhase.FLOP,
            players_in_hand=players,
        )

        expected_order = [
            Seat.SEAT_1,  # SB
            Seat.SEAT_2,  # BB
            Seat.SEAT_3,  # UTG
            Seat.SEAT_4,  # UTG+1
            Seat.SEAT_5,  # CO
            Seat.SEAT_0,  # BTN
        ]
        assert betting_order == expected_order

    def test_postflop_order_consistent_across_flop_turn_river(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="btn",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="sb",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="bb",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="utg",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        flop_order = PositionManager.get_betting_order(
            mapping, HandPhase.FLOP, players
        )
        turn_order = PositionManager.get_betting_order(
            mapping, HandPhase.TURN, players
        )
        river_order = PositionManager.get_betting_order(
            mapping, HandPhase.RIVER, players
        )

        assert flop_order == turn_order == river_order


class TestHeadsUpActionOrder:
    """Heads-up special rules: Button/SB acts first preflop, BB acts first postflop."""

    def test_heads_up_preflop_button_sb_acts_first(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="btn_sb",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="bb",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        betting_order = PositionManager.get_betting_order(
            position_mapping=mapping,
            phase=HandPhase.PRE_FLOP,
            players_in_hand=players,
        )

        assert betting_order[0] == Seat.SEAT_0  # BTN/SB acts first preflop
        assert betting_order[1] == Seat.SEAT_1  # BB acts second

    def test_heads_up_postflop_bb_acts_first(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="btn_sb",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="bb",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        betting_order = PositionManager.get_betting_order(
            position_mapping=mapping,
            phase=HandPhase.FLOP,
            players_in_hand=players,
        )

        assert betting_order[0] == Seat.SEAT_1  # BB acts first postflop
        assert betting_order[1] == Seat.SEAT_0  # BTN/SB acts second (last)

    def test_heads_up_button_sb_acts_last_postflop(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="btn_sb",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="bb",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        for phase in [HandPhase.FLOP, HandPhase.TURN, HandPhase.RIVER]:
            betting_order = PositionManager.get_betting_order(
                mapping, phase, players
            )
            assert (
                betting_order[-1] == Seat.SEAT_0
            )  # BTN/SB always last postflop


class TestButtonRotation:
    """Button moves clockwise after each hand."""

    def test_button_advances_to_next_seat_clockwise(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        new_button = PositionManager.advance_button(
            all_players=players,
            current_button_seat=Seat.SEAT_0,
        )

        assert new_button == Seat.SEAT_1

    def test_button_wraps_around_table(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        new_button = PositionManager.advance_button(
            all_players=players,
            current_button_seat=Seat.SEAT_2,
        )

        assert new_button == Seat.SEAT_0

    def test_first_hand_button_does_not_advance(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        assert mapping.button_seat == Seat.SEAT_0

    def test_subsequent_hand_button_advances(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=True,
        )

        assert mapping.button_seat == Seat.SEAT_1


class TestSkipEliminatedPlayers:
    """Position calculations skip eliminated players."""

    def test_button_skips_eliminated_player(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        new_button = PositionManager.advance_button(
            all_players=players,
            current_button_seat=Seat.SEAT_0,
        )

        assert new_button == Seat.SEAT_2  # Skips seat 1 (eliminated)

    def test_small_blind_skips_eliminated_player(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="btn",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="eliminated",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                player_id="sb",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="bb",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        assert mapping.small_blind_seat == Seat.SEAT_2  # Skips seat 1

    def test_big_blind_skips_eliminated_player(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="btn",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="sb",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="eliminated",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                player_id="bb",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        assert mapping.big_blind_seat == Seat.SEAT_3  # Skips seat 2

    def test_eliminated_players_excluded_from_betting_order(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="eliminated",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        players_in_hand = [p for p in players if p.is_in_hand()]
        betting_order = PositionManager.get_betting_order(
            mapping, HandPhase.PRE_FLOP, players_in_hand
        )

        assert Seat.SEAT_1 not in betting_order
        assert len(betting_order) == 2

    def test_six_to_two_players_with_eliminations(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="e1",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                player_id="e2",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                player_id="e3",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                player_id="e4",
                seat=Seat.SEAT_4,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                player_id="p6",
                seat=Seat.SEAT_5,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        assert mapping.is_heads_up is True
        assert mapping.button_seat == mapping.small_blind_seat


class TestFoldedPlayersInBettingOrder:
    """Folded players are excluded from betting order during the hand."""

    def test_folded_players_not_in_betting_order(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="btn",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="folded",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
                participation_status=HandParticipationStatus.FOLDED,
            ),
            sample_player_factory(
                player_id="bb",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        players_in_hand = [p for p in players if p.is_in_hand()]
        betting_order = PositionManager.get_betting_order(
            mapping, HandPhase.FLOP, players_in_hand
        )

        assert Seat.SEAT_1 not in betting_order


class TestTablePositionMappingValidation:
    """TablePositionMapping validates its invariants."""

    def test_heads_up_requires_button_equals_small_blind(self) -> None:
        with pytest.raises(
            ValueError, match="button_seat must equal small_blind_seat"
        ):
            _ = TablePositionMapping(
                button_seat=Seat.SEAT_0,
                small_blind_seat=Seat.SEAT_1,  # Different from button
                big_blind_seat=Seat.SEAT_2,
                utg_seat=None,
                utg_plus_one_seat=None,
                cutoff_seat=None,
                is_heads_up=True,
                active_players_count=2,
                total_seats_at_table=3,
            )

    def test_heads_up_requires_exactly_two_active_players(self) -> None:
        with pytest.raises(
            ValueError, match="Heads-up requires 2 active players"
        ):
            _ = TablePositionMapping(
                button_seat=Seat.SEAT_0,
                small_blind_seat=Seat.SEAT_0,
                big_blind_seat=Seat.SEAT_1,
                utg_seat=None,
                utg_plus_one_seat=None,
                cutoff_seat=None,
                is_heads_up=True,
                active_players_count=3,
                total_seats_at_table=4,
            )

    def test_active_players_must_be_at_least_two(self) -> None:
        with pytest.raises(
            ValueError, match="Active players count must be at least 2"
        ):
            _ = TablePositionMapping(
                button_seat=Seat.SEAT_0,
                small_blind_seat=Seat.SEAT_1,
                big_blind_seat=Seat.SEAT_2,
                utg_seat=None,
                utg_plus_one_seat=None,
                cutoff_seat=None,
                is_heads_up=False,
                active_players_count=1,
                total_seats_at_table=3,
            )


class TestPositionManagerValidation:
    """PositionManager validates input state."""

    def test_requires_at_least_two_players(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        with pytest.raises(ValueError, match="Need at least 2 players"):
            _ = PositionManager.resolve_positions_for_hand(
                all_players=players,
                previous_button_seat=Seat.SEAT_0,
                advance_button=False,
            )

    def test_requires_at_least_two_active_players(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="eliminated",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
        ]

        with pytest.raises(ValueError, match="Need at least 2 active players"):
            _ = PositionManager.resolve_positions_for_hand(
                all_players=players,
                previous_button_seat=Seat.SEAT_0,
                advance_button=False,
            )


class TestGetSeatForPosition:
    """TablePositionMapping.get_seat_for_position returns correct seat or None."""

    def test_returns_button_seat(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p4",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        assert (
            mapping.get_seat_for_position(PositionName.BUTTON) == Seat.SEAT_0
        )

    def test_returns_small_blind_seat(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p4",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        assert (
            mapping.get_seat_for_position(PositionName.SMALL_BLIND)
            == Seat.SEAT_1
        )

    def test_returns_big_blind_seat(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p4",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        assert (
            mapping.get_seat_for_position(PositionName.BIG_BLIND)
            == Seat.SEAT_2
        )

    def test_returns_none_for_missing_position(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        assert (
            mapping.get_seat_for_position(PositionName.UNDER_THE_GUN) is None
        )
        assert mapping.get_seat_for_position(PositionName.UTG_PLUS_ONE) is None
        assert mapping.get_seat_for_position(PositionName.CUTOFF) is None


class TestPositionMappingWithNonContiguousSeats:
    """Position system works correctly when eliminated players create gaps in seating."""

    def test_positions_with_gap_in_middle_of_table(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="eliminated",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p4",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        assert mapping.button_seat == Seat.SEAT_0
        assert (
            mapping.small_blind_seat == Seat.SEAT_2
        )  # Skips eliminated seat 1
        assert mapping.big_blind_seat == Seat.SEAT_3
        assert mapping.active_players_count == 3

    def test_positions_with_multiple_gaps(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="e1",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="e2",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                player_id="p5",
                seat=Seat.SEAT_4,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p6",
                seat=Seat.SEAT_5,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        assert mapping.active_players_count == 4
        assert mapping.button_seat == Seat.SEAT_0
        assert mapping.small_blind_seat == Seat.SEAT_2
        assert mapping.big_blind_seat == Seat.SEAT_4
        assert mapping.utg_seat == Seat.SEAT_5


class TestButtonRotationWithEliminations:
    """Button rotation correctly handles eliminated players over multiple hands."""

    def test_button_rotates_through_active_players_only(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="e1",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="e2",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                player_id="p5",
                seat=Seat.SEAT_4,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        # Track button through multiple advances
        button = Seat.SEAT_0
        visited_buttons: list[Seat] = [button]

        for _ in range(5):  # Rotate enough to see the pattern
            button = PositionManager.advance_button(players, button)
            visited_buttons.append(button)

        # Should only visit active seats: 0, 2, 4
        for btn in visited_buttons:
            assert btn in [Seat.SEAT_0, Seat.SEAT_2, Seat.SEAT_4]

    def test_button_skips_multiple_consecutive_eliminated_players(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="e1",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                player_id="e2",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                player_id="e3",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                player_id="p5",
                seat=Seat.SEAT_4,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        new_button = PositionManager.advance_button(players, Seat.SEAT_0)

        assert new_button == Seat.SEAT_4  # Skips seats 1, 2, 3


class TestActionOrderWithFewPlayers:
    """Action order adapts correctly to smaller table sizes."""

    def test_three_player_preflop_order_is_btn_sb_bb(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="btn",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="sb",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="bb",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        betting_order = PositionManager.get_betting_order(
            mapping, HandPhase.PRE_FLOP, players
        )

        # In 3-player, btn acts first preflop, then sb, then bb
        assert betting_order == [Seat.SEAT_0, Seat.SEAT_1, Seat.SEAT_2]

    def test_three_player_postflop_order_is_sb_bb_btn(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="btn",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="sb",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="bb",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        betting_order = PositionManager.get_betting_order(
            mapping, HandPhase.FLOP, players
        )

        assert betting_order == [Seat.SEAT_1, Seat.SEAT_2, Seat.SEAT_0]

    def test_four_player_preflop_order_includes_utg(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="btn",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="sb",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="bb",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="utg",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        betting_order = PositionManager.get_betting_order(
            mapping, HandPhase.PRE_FLOP, players
        )

        # UTG acts first preflop in 4+ player game
        assert betting_order[0] == Seat.SEAT_3
        assert betting_order[-1] == Seat.SEAT_2  # BB last


class TestTransitionToHeadsUp:
    """When table goes from 3 to 2 players, heads-up rules apply."""

    def test_three_to_two_becomes_heads_up(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="eliminated",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        assert mapping.is_heads_up is True
        assert mapping.button_seat == mapping.small_blind_seat

    def test_heads_up_action_order_after_elimination(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="btn_sb",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="eliminated",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                player_id="bb",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        active_players = [p for p in players if p.is_in_hand()]

        preflop_order = PositionManager.get_betting_order(
            mapping, HandPhase.PRE_FLOP, active_players
        )
        postflop_order = PositionManager.get_betting_order(
            mapping, HandPhase.FLOP, active_players
        )

        assert preflop_order == [Seat.SEAT_0, Seat.SEAT_2]  # BTN/SB first
        assert postflop_order == [Seat.SEAT_2, Seat.SEAT_0]  # BB first


class TestBettingOrderPhaseValidity:
    """get_betting_order raises error for invalid phases."""

    def test_showdown_phase_raises_error(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        with pytest.raises(ValueError, match="No betting order rule"):
            _ = PositionManager.get_betting_order(
                mapping, HandPhase.SHOWDOWN, players
            )


class TestHeadsUpTransitionButtonEliminated:
    """Heads-up transition when the button holder is eliminated (RULE_BOOK 14.3)."""

    def test_button_moves_when_button_holder_eliminated(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """When 3→2 players and button player eliminated, button moves to next active."""
        players = [
            sample_player_factory(
                player_id="former_btn",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=True,
        )

        assert mapping.button_seat == Seat.SEAT_1
        assert mapping.is_heads_up is True

    def test_heads_up_positions_correct_after_button_holder_eliminated(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """After button holder eliminated, new button is SB in heads-up."""
        players = [
            sample_player_factory(
                player_id="eliminated",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                player_id="new_btn_sb",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="bb",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=True,
        )

        assert mapping.button_seat == mapping.small_blind_seat
        assert mapping.big_blind_seat == Seat.SEAT_2

    def test_action_order_correct_after_button_holder_eliminated(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Action order follows heads-up rules after button holder eliminated."""
        players = [
            sample_player_factory(
                player_id="eliminated",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                player_id="new_btn_sb",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="bb",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=True,
        )

        active_players = [p for p in players if p.is_in_hand()]

        preflop_order = PositionManager.get_betting_order(
            mapping, HandPhase.PRE_FLOP, active_players
        )
        postflop_order = PositionManager.get_betting_order(
            mapping, HandPhase.FLOP, active_players
        )

        assert preflop_order == [
            Seat.SEAT_1,
            Seat.SEAT_2,
        ]  # BTN/SB first preflop
        assert postflop_order == [
            Seat.SEAT_2,
            Seat.SEAT_1,
        ]  # BB first postflop


class TestBettingOrderWithMidHandFolds:
    """Betting order excludes players who folded during the hand."""

    def test_postflop_order_excludes_sb_who_folded_preflop(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """SB folds preflop; postflop order starts with BB."""
        players = [
            sample_player_factory(
                player_id="btn",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="sb_folded",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
                participation_status=HandParticipationStatus.FOLDED,
            ),
            sample_player_factory(
                player_id="bb",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="utg",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        players_in_hand = [p for p in players if p.is_in_hand()]
        betting_order = PositionManager.get_betting_order(
            mapping, HandPhase.FLOP, players_in_hand
        )

        assert betting_order[0] == Seat.SEAT_2  # BB is first (SB folded)
        assert Seat.SEAT_1 not in betting_order

    def test_postflop_order_excludes_bb_who_folded_preflop(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """BB folds preflop; postflop order starts with UTG."""
        players = [
            sample_player_factory(
                player_id="btn",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="sb",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="bb_folded",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
                participation_status=HandParticipationStatus.FOLDED,
            ),
            sample_player_factory(
                player_id="utg",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        players_in_hand = [p for p in players if p.is_in_hand()]
        betting_order = PositionManager.get_betting_order(
            mapping, HandPhase.FLOP, players_in_hand
        )

        assert betting_order[0] == Seat.SEAT_1  # SB is first
        assert betting_order[1] == Seat.SEAT_3  # UTG is second (BB folded)
        assert Seat.SEAT_2 not in betting_order

    def test_preflop_order_excludes_utg_who_folded(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """If UTG folds during preflop action, they're excluded from order."""
        players = [
            sample_player_factory(
                player_id="btn",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="sb",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="bb",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="utg_folded",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
                participation_status=HandParticipationStatus.FOLDED,
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        players_in_hand = [p for p in players if p.is_in_hand()]
        betting_order = PositionManager.get_betting_order(
            mapping, HandPhase.PRE_FLOP, players_in_hand
        )

        assert Seat.SEAT_3 not in betting_order
        assert betting_order == [Seat.SEAT_0, Seat.SEAT_1, Seat.SEAT_2]

    def test_heads_up_postflop_when_only_two_remain_after_folds(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Four players start, two fold preflop; postflop order is correct."""
        players = [
            sample_player_factory(
                player_id="btn",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="sb_folded",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
                participation_status=HandParticipationStatus.FOLDED,
            ),
            sample_player_factory(
                player_id="bb",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="utg_folded",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
                participation_status=HandParticipationStatus.FOLDED,
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        players_in_hand = [p for p in players if p.is_in_hand()]
        betting_order = PositionManager.get_betting_order(
            mapping, HandPhase.FLOP, players_in_hand
        )

        # Note: mapping.is_heads_up is False (4 active players at hand start)
        # But betting order correctly filters to only players still in hand
        assert betting_order == [Seat.SEAT_2, Seat.SEAT_0]  # BB then BTN


class TestAllInPlayersInBettingOrder:
    """All-in players are included or excluded based on caller's filter."""

    def test_all_in_player_included_when_passed_to_betting_order(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """All-in player appears in order when included in players_in_hand."""
        players = [
            sample_player_factory(
                player_id="btn",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="sb_all_in",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(0),
                total_invested_this_hand=ChipAmount(500),
            ),
            sample_player_factory(
                player_id="bb",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        # Caller includes all-in player (is_in_hand() returns True for all-in)
        players_in_hand = [p for p in players if p.is_in_hand()]
        betting_order = PositionManager.get_betting_order(
            mapping, HandPhase.FLOP, players_in_hand
        )

        assert Seat.SEAT_1 in betting_order

    def test_all_in_player_excluded_when_filtered_by_caller(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """All-in player excluded when caller filters them out."""
        players = [
            sample_player_factory(
                player_id="btn",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="sb_all_in",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(0),
                total_invested_this_hand=ChipAmount(500),
            ),
            sample_player_factory(
                player_id="bb",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_0,
            advance_button=False,
        )

        # Caller explicitly excludes all-in players
        players_who_can_act = [
            p for p in players if p.is_in_hand() and p.has_chips()
        ]
        betting_order = PositionManager.get_betting_order(
            mapping, HandPhase.FLOP, players_who_can_act
        )

        assert Seat.SEAT_1 not in betting_order
        assert betting_order == [Seat.SEAT_2, Seat.SEAT_0]


class TestButtonRotationEdgeCases:
    """Edge cases in button rotation."""

    def test_button_advances_full_circle_back_to_original(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Button advances through all players and returns to start."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        button = Seat.SEAT_0
        for _ in range(3):
            button = PositionManager.advance_button(players, button)

        assert button == Seat.SEAT_0

    def test_button_skips_all_eliminated_between_two_active(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Button correctly skips all eliminated players to find next active."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="e1",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                player_id="e2",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                player_id="e3",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                player_id="e4",
                seat=Seat.SEAT_4,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                player_id="p6",
                seat=Seat.SEAT_5,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        new_button = PositionManager.advance_button(players, Seat.SEAT_0)

        assert new_button == Seat.SEAT_5

    def test_button_wraps_around_skipping_eliminated_at_table_end(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Button wraps from end of table to beginning, skipping eliminated."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="e1",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="e2",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
        ]

        # Button at seat 2, should wrap to seat 0 (skipping eliminated seats 3 and 1)
        new_button = PositionManager.advance_button(players, Seat.SEAT_2)

        assert new_button == Seat.SEAT_0


class TestPositionAssignmentWithWraparound:
    """Position assignment correctly wraps around the table."""

    def test_four_player_positions_wrap_around(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Positions wrap correctly when button is near end of table."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p4",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_2,
            advance_button=False,
        )

        assert mapping.button_seat == Seat.SEAT_2
        assert mapping.small_blind_seat == Seat.SEAT_3
        assert mapping.big_blind_seat == Seat.SEAT_0  # Wraps around
        assert mapping.utg_seat == Seat.SEAT_1

    def test_three_player_positions_wrap_around(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Three player positions wrap correctly."""
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=Seat.SEAT_2,
            advance_button=False,
        )

        assert mapping.button_seat == Seat.SEAT_2
        assert mapping.small_blind_seat == Seat.SEAT_0  # Wraps around
        assert mapping.big_blind_seat == Seat.SEAT_1


class TestMultiHandTournamentScenario:
    """Scenario test: simulate a full tournament from 6 players to winner.

    This test simulates a complete tournament progression:
    - Starts with 6 players
    - Plays multiple hands with button rotation
    - Eliminates players at realistic points
    - Verifies positions are correct at each stage
    - Ends when only one player remains

    Per RULE_BOOK.md sections 3, 6.2, and 14.
    """

    def test_full_tournament_from_six_players_to_winner(
        self, sample_player_factory: Callable[..., Player]
    ) -> None:
        """Simulate complete tournament tracking positions through all eliminations."""
        # === SETUP: 6 players at seats 0-5 ===
        players = [
            sample_player_factory(
                player_id="alice",
                seat=Seat.SEAT_0,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="bob",
                seat=Seat.SEAT_1,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="carol",
                seat=Seat.SEAT_2,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="dan",
                seat=Seat.SEAT_3,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="eve",
                seat=Seat.SEAT_4,
                remaining_chips=ChipAmount(1000),
            ),
            sample_player_factory(
                player_id="frank",
                seat=Seat.SEAT_5,
                remaining_chips=ChipAmount(1000),
            ),
        ]

        def get_active_players() -> list[Player]:
            return [
                p
                for p in players
                if p.participation_status != HandParticipationStatus.ELIMINATED
            ]

        def eliminate_player(player_id: str) -> None:
            nonlocal players
            for i, p in enumerate(players):
                if p.id == player_id:
                    players[i] = replace(
                        p,
                        participation_status=HandParticipationStatus.ELIMINATED,
                        remaining_chips=ChipAmount(0),
                    )
                    break

        current_button_seat = Seat.SEAT_0

        # =========================================================
        # HAND 1: 6 players, first hand (button at seat 0)
        # =========================================================
        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=current_button_seat,
            advance_button=False,
        )

        assert (
            mapping.button_seat == Seat.SEAT_0
        ), "Hand 1: Button should be at seat 0"
        assert (
            mapping.small_blind_seat == Seat.SEAT_1
        ), "Hand 1: SB should be at seat 1"
        assert (
            mapping.big_blind_seat == Seat.SEAT_2
        ), "Hand 1: BB should be at seat 2"
        assert (
            mapping.utg_seat == Seat.SEAT_3
        ), "Hand 1: UTG should be at seat 3"
        assert (
            mapping.utg_plus_one_seat == Seat.SEAT_4
        ), "Hand 1: UTG+1 should be at seat 4"
        assert (
            mapping.cutoff_seat == Seat.SEAT_5
        ), "Hand 1: CO should be at seat 5"
        assert mapping.active_players_count == 6
        assert mapping.is_heads_up is False

        # Verify preflop order: UTG → UTG+1 → CO → BTN → SB → BB
        preflop_order = PositionManager.get_betting_order(
            mapping, HandPhase.PRE_FLOP, get_active_players()
        )
        assert preflop_order == [
            Seat.SEAT_3,
            Seat.SEAT_4,
            Seat.SEAT_5,
            Seat.SEAT_0,
            Seat.SEAT_1,
            Seat.SEAT_2,
        ], "Hand 1: Preflop order should be UTG→UTG+1→CO→BTN→SB→BB"

        # Verify postflop order: SB → BB → UTG → UTG+1 → CO → BTN
        postflop_order = PositionManager.get_betting_order(
            mapping, HandPhase.FLOP, get_active_players()
        )
        assert postflop_order == [
            Seat.SEAT_1,
            Seat.SEAT_2,
            Seat.SEAT_3,
            Seat.SEAT_4,
            Seat.SEAT_5,
            Seat.SEAT_0,
        ], "Hand 1: Postflop order should be SB→BB→UTG→UTG+1→CO→BTN"

        current_button_seat = mapping.button_seat

        # =========================================================
        # HAND 2: 6 players, button advances to seat 1
        # =========================================================
        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=current_button_seat,
            advance_button=True,
        )

        assert (
            mapping.button_seat == Seat.SEAT_1
        ), "Hand 2: Button should advance to seat 1"
        assert (
            mapping.small_blind_seat == Seat.SEAT_2
        ), "Hand 2: SB should be at seat 2"
        assert (
            mapping.big_blind_seat == Seat.SEAT_3
        ), "Hand 2: BB should be at seat 3"
        assert (
            mapping.utg_seat == Seat.SEAT_4
        ), "Hand 2: UTG should be at seat 4"
        assert (
            mapping.utg_plus_one_seat == Seat.SEAT_5
        ), "Hand 2: UTG+1 should be at seat 5"
        assert (
            mapping.cutoff_seat == Seat.SEAT_0
        ), "Hand 2: CO should wrap to seat 0"

        current_button_seat = mapping.button_seat

        # =========================================================
        # HAND 3: Dan (seat 3) eliminated → 5 players
        # =========================================================
        eliminate_player("dan")
        assert len(get_active_players()) == 5

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=current_button_seat,
            advance_button=True,
        )

        assert (
            mapping.button_seat == Seat.SEAT_2
        ), "Hand 3: Button should advance to seat 2"
        assert (
            mapping.small_blind_seat == Seat.SEAT_4
        ), "Hand 3: SB skips eliminated seat 3"
        assert (
            mapping.big_blind_seat == Seat.SEAT_5
        ), "Hand 3: BB should be at seat 5"
        assert mapping.active_players_count == 5
        assert (
            mapping.utg_seat == Seat.SEAT_0
        ), "Hand 3: UTG should be at seat 0"
        assert (
            mapping.utg_plus_one_seat is None
        ), "Hand 3: No UTG+1 with 5 players"
        assert (
            mapping.cutoff_seat == Seat.SEAT_1
        ), "Hand 3: CO should be at seat 1"

        # Verify preflop order with 5 players: UTG → CO → BTN → SB → BB
        preflop_order = PositionManager.get_betting_order(
            mapping, HandPhase.PRE_FLOP, get_active_players()
        )
        assert preflop_order == [
            Seat.SEAT_0,
            Seat.SEAT_1,
            Seat.SEAT_2,
            Seat.SEAT_4,
            Seat.SEAT_5,
        ], "Hand 3: Preflop order for 5 players"

        current_button_seat = mapping.button_seat

        # =========================================================
        # HAND 4: Eve (seat 4) and Frank (seat 5) eliminated → 3 players
        # =========================================================
        eliminate_player("eve")
        eliminate_player("frank")
        assert len(get_active_players()) == 3

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=current_button_seat,
            advance_button=True,
        )

        # Button should skip seats 3, 4, 5 (all eliminated) and land on seat 0
        assert (
            mapping.button_seat == Seat.SEAT_0
        ), "Hand 4: Button skips eliminated, lands on seat 0"
        assert mapping.small_blind_seat == Seat.SEAT_1, "Hand 4: SB at seat 1"
        assert mapping.big_blind_seat == Seat.SEAT_2, "Hand 4: BB at seat 2"
        assert mapping.active_players_count == 3
        assert mapping.utg_seat is None, "Hand 4: No UTG with 3 players"
        assert mapping.cutoff_seat is None, "Hand 4: No CO with 3 players"
        assert mapping.is_heads_up is False

        # 3-player preflop: BTN → SB → BB
        preflop_order = PositionManager.get_betting_order(
            mapping, HandPhase.PRE_FLOP, get_active_players()
        )
        assert preflop_order == [
            Seat.SEAT_0,
            Seat.SEAT_1,
            Seat.SEAT_2,
        ], "Hand 4: 3-player preflop order"

        # 3-player postflop: SB → BB → BTN
        postflop_order = PositionManager.get_betting_order(
            mapping, HandPhase.FLOP, get_active_players()
        )
        assert postflop_order == [
            Seat.SEAT_1,
            Seat.SEAT_2,
            Seat.SEAT_0,
        ], "Hand 4: 3-player postflop order"

        current_button_seat = mapping.button_seat

        # =========================================================
        # HAND 5: Button advances, still 3 players
        # =========================================================
        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=current_button_seat,
            advance_button=True,
        )

        assert (
            mapping.button_seat == Seat.SEAT_1
        ), "Hand 5: Button advances to seat 1"
        assert mapping.small_blind_seat == Seat.SEAT_2, "Hand 5: SB at seat 2"
        assert (
            mapping.big_blind_seat == Seat.SEAT_0
        ), "Hand 5: BB wraps to seat 0"

        current_button_seat = mapping.button_seat

        # =========================================================
        # HAND 6: Carol (seat 2) eliminated → HEADS UP (2 players)
        # =========================================================
        eliminate_player("carol")
        assert len(get_active_players()) == 2

        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=current_button_seat,
            advance_button=True,
        )

        # Button advances, skipping eliminated seat 2
        assert (
            mapping.button_seat == Seat.SEAT_0
        ), "Hand 6: Button skips seat 2, lands on seat 0"
        assert mapping.is_heads_up is True, "Hand 6: Should be heads-up"
        assert (
            mapping.button_seat == mapping.small_blind_seat
        ), "Hand 6: Button is SB in heads-up"
        assert (
            mapping.big_blind_seat == Seat.SEAT_1
        ), "Hand 6: BB is the other player"
        assert mapping.active_players_count == 2

        # Heads-up preflop: BTN/SB acts first
        preflop_order = PositionManager.get_betting_order(
            mapping, HandPhase.PRE_FLOP, get_active_players()
        )
        assert preflop_order == [
            Seat.SEAT_0,
            Seat.SEAT_1,
        ], "Hand 6: Heads-up preflop BTN/SB first"

        # Heads-up postflop: BB acts first
        postflop_order = PositionManager.get_betting_order(
            mapping, HandPhase.FLOP, get_active_players()
        )
        assert postflop_order == [
            Seat.SEAT_1,
            Seat.SEAT_0,
        ], "Hand 6: Heads-up postflop BB first"

        current_button_seat = mapping.button_seat

        # =========================================================
        # HAND 7: Heads-up continues, button alternates
        # =========================================================
        mapping = PositionManager.resolve_positions_for_hand(
            all_players=players,
            previous_button_seat=current_button_seat,
            advance_button=True,
        )

        assert (
            mapping.button_seat == Seat.SEAT_1
        ), "Hand 7: Button alternates to seat 1"
        assert (
            mapping.button_seat == mapping.small_blind_seat
        ), "Hand 7: Button is still SB"
        assert (
            mapping.big_blind_seat == Seat.SEAT_0
        ), "Hand 7: BB is now seat 0"

        # Verify heads-up action order flipped
        preflop_order = PositionManager.get_betting_order(
            mapping, HandPhase.PRE_FLOP, get_active_players()
        )
        assert preflop_order == [
            Seat.SEAT_1,
            Seat.SEAT_0,
        ], "Hand 7: BTN/SB (seat 1) acts first preflop"

        postflop_order = PositionManager.get_betting_order(
            mapping, HandPhase.TURN, get_active_players()
        )
        assert postflop_order == [
            Seat.SEAT_0,
            Seat.SEAT_1,
        ], "Hand 7: BB (seat 0) acts first postflop"

        current_button_seat = mapping.button_seat

        # =========================================================
        # HAND 8: Final hand - Bob (seat 1) eliminated → Alice wins
        # =========================================================
        eliminate_player("bob")
        assert len(get_active_players()) == 1

        # Tournament is over - only Alice remains
        final_player = get_active_players()[0]
        assert (
            final_player.id == "alice"
        ), "Alice should be the tournament winner"
        assert final_player.seat == Seat.SEAT_0

        # Verify we cannot start a new hand with only 1 player
        with pytest.raises(ValueError, match="Need at least 2 active players"):
            _ = PositionManager.resolve_positions_for_hand(
                all_players=players,
                previous_button_seat=current_button_seat,
                advance_button=True,
            )
