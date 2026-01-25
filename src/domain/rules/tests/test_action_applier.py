"""Tests for ActionApplier - applies validated actions to game state."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from src.domain.models.actions import Action, ActionType
from src.domain.models.card import Rank, Suit
from src.domain.models.chips import ChipAmount
from src.domain.models.game import NO_POSITION_TO_ACT, Game, HandPhase
from src.domain.models.player import (
    BettingRoundActionStatus,
    HandParticipationStatus,
    Player,
)
from src.domain.models.seat import Seat
from src.domain.rules.action_applier import ActionApplier

from .conftest import (
    BIG_BLIND_STANDARD,
    LARGE_CHIPS,
    MEDIUM_CHIPS,
    make_card,
    make_hand,
)


class TestFoldAction:
    """Tests for FOLD action application."""

    def test_fold_sets_player_participation_status_to_folded(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.FOLD)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert (
            updated_player.participation_status
            == HandParticipationStatus.FOLDED
        )

    def test_fold_sets_player_betting_status_to_acted(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.FOLD)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.betting_status == BettingRoundActionStatus.ACTED

    def test_fold_preserves_player_hole_cards(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        hole_cards = make_hand(
            make_card(rank=Rank.ACE, suit=Suit.SPADES),
            make_card(rank=Rank.KING, suit=Suit.HEARTS),
        )
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
            hole_cards=hole_cards,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.FOLD)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.hole_cards == hole_cards

    def test_fold_does_not_change_player_chips(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        initial_chips = MEDIUM_CHIPS
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=initial_chips,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.FOLD)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.remaining_chips == initial_chips

    def test_fold_does_not_change_total_invested_this_hand(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        initial_invested = ChipAmount(50)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=initial_invested,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=initial_invested,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.FOLD)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.total_invested_this_hand == initial_invested

    def test_fold_does_not_reset_other_players_betting_status(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.FOLD)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert (
            updated_other_player.betting_status
            == BettingRoundActionStatus.ACTED
        )

    def test_fold_preserves_last_raise_increment_after_previous_raise(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        raise_increment = ChipAmount(50)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, other_player], last_raise_increment=raise_increment
        )
        action = Action(action_type=ActionType.FOLD)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        assert (
            updated_game.betting_state.last_raise_increment == raise_increment
        )


class TestCheckAction:
    """Tests for CHECK action application."""

    def test_check_sets_player_betting_status_to_acted(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.betting_status == BettingRoundActionStatus.ACTED

    def test_check_does_not_change_player_chips(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        initial_chips = MEDIUM_CHIPS
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=initial_chips,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.remaining_chips == initial_chips

    def test_check_does_not_change_total_invested_this_hand(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        initial_invested = ChipAmount(50)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=initial_invested,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=initial_invested,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.total_invested_this_hand == initial_invested

    def test_check_does_not_change_participation_status(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert (
            updated_player.participation_status
            == HandParticipationStatus.IN_HAND
        )

    def test_check_does_not_reset_other_players_betting_status(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert (
            updated_other_player.betting_status
            == BettingRoundActionStatus.ACTED
        )

    def test_check_preserves_last_raise_increment_after_previous_raise(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        raise_increment = ChipAmount(50)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, other_player], last_raise_increment=raise_increment
        )
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        assert (
            updated_game.betting_state.last_raise_increment == raise_increment
        )


class TestCallAction:
    """Tests for CALL action application."""

    def test_call_reduces_player_chips_by_call_amount(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        initial_chips = ChipAmount(100)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=initial_chips,
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.CALL)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.remaining_chips == ChipAmount(70)

    def test_call_increases_total_invested_this_hand_by_call_amount(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        initial_invested = ChipAmount(20)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=initial_invested,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.CALL)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.total_invested_this_hand == ChipAmount(50)

    def test_call_sets_player_betting_status_to_acted(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.CALL)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.betting_status == BettingRoundActionStatus.ACTED

    def test_call_when_player_has_insufficient_chips_calls_with_all_remaining_chips(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        initial_chips = ChipAmount(20)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=initial_chips,
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.ALL_IN, amount=initial_chips)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.remaining_chips == ChipAmount(0)
        assert updated_player.total_invested_this_hand == ChipAmount(40)

    def test_call_does_not_reset_other_players_betting_status(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.CALL)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert (
            updated_other_player.betting_status
            == BettingRoundActionStatus.ACTED
        )

    def test_call_preserves_last_raise_increment_after_previous_raise(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        raise_increment = ChipAmount(50)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, other_player], last_raise_increment=raise_increment
        )
        action = Action(action_type=ActionType.CALL)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        assert (
            updated_game.betting_state.last_raise_increment == raise_increment
        )


class TestRaiseAction:
    """Tests for RAISE action application."""

    def test_raise_reduces_player_chips_by_call_amount_plus_raise_increment(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        initial_chips = ChipAmount(200)
        raise_increment = ChipAmount(50)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=initial_chips,
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, other_player], last_raise_increment=BIG_BLIND_STANDARD
        )
        action = Action(action_type=ActionType.RAISE, amount=raise_increment)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.remaining_chips == ChipAmount(120)

    def test_raise_increases_total_invested_this_hand_by_call_amount_plus_raise_increment(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        initial_invested = ChipAmount(20)
        raise_increment = ChipAmount(50)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=initial_invested,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, other_player], last_raise_increment=BIG_BLIND_STANDARD
        )
        action = Action(action_type=ActionType.RAISE, amount=raise_increment)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.total_invested_this_hand == ChipAmount(100)

    def test_raise_sets_player_betting_status_to_acted(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        raise_increment = ChipAmount(50)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, other_player], last_raise_increment=BIG_BLIND_STANDARD
        )
        action = Action(action_type=ActionType.RAISE, amount=raise_increment)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.betting_status == BettingRoundActionStatus.ACTED

    def test_raise_resets_other_acted_players_to_needs_action(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        raise_increment = ChipAmount(50)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, other_player], last_raise_increment=BIG_BLIND_STANDARD
        )
        action = Action(action_type=ActionType.RAISE, amount=raise_increment)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert (
            updated_other_player.betting_status
            == BettingRoundActionStatus.NEEDS_ACTION
        )

    def test_raise_does_not_reset_folded_players(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        raise_increment = ChipAmount(50)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        acted_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        folded_player = sample_player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=LARGE_CHIPS,
            participation_status=HandParticipationStatus.FOLDED,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, acted_player, folded_player],
            last_raise_increment=BIG_BLIND_STANDARD,
        )
        action = Action(action_type=ActionType.RAISE, amount=raise_increment)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_folded_player = updated_game.get_player_by_id(folded_player.id)
        assert updated_folded_player is not None
        assert (
            updated_folded_player.betting_status
            == BettingRoundActionStatus.ACTED
        )

    def test_raise_does_not_reset_raising_player(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        raise_increment = ChipAmount(50)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, other_player], last_raise_increment=BIG_BLIND_STANDARD
        )
        action = Action(action_type=ActionType.RAISE, amount=raise_increment)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.betting_status == BettingRoundActionStatus.ACTED

    def test_raise_updates_betting_state_last_raise_increment(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        raise_increment = ChipAmount(50)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, other_player], last_raise_increment=BIG_BLIND_STANDARD
        )
        action = Action(action_type=ActionType.RAISE, amount=raise_increment)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        assert (
            updated_game.betting_state.last_raise_increment == raise_increment
        )

    def test_last_raise_increment_preserved_through_multiple_calls_after_raise(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        raise_increment = ChipAmount(50)
        player_a = sample_player_factory(
            player_id="player-a",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        player_b = sample_player_factory(
            player_id="player-b",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        player_c = sample_player_factory(
            player_id="player-c",
            seat=Seat.SEAT_2,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player_a, player_b, player_c],
            last_raise_increment=BIG_BLIND_STANDARD,
        )

        raise_action = Action(
            action_type=ActionType.RAISE, amount=raise_increment
        )
        game_after_raise = ActionApplier.apply_action(
            game, player_a.id, raise_action
        )
        assert (
            game_after_raise.betting_state.last_raise_increment
            == raise_increment
        )

        updated_player_b = game_after_raise.get_player_by_id(player_b.id)
        assert updated_player_b is not None
        assert (
            updated_player_b.betting_status
            == BettingRoundActionStatus.NEEDS_ACTION
        )

        updated_player_c = game_after_raise.get_player_by_id(player_c.id)
        assert updated_player_c is not None
        assert (
            updated_player_c.betting_status
            == BettingRoundActionStatus.NEEDS_ACTION
        )

        call_action = Action(action_type=ActionType.CALL)
        game_after_call_b = ActionApplier.apply_action(
            game_after_raise, updated_player_b.id, call_action
        )
        assert (
            game_after_call_b.betting_state.last_raise_increment
            == raise_increment
        )

        game_after_call_c = ActionApplier.apply_action(
            game_after_call_b, updated_player_c.id, call_action
        )
        assert (
            game_after_call_c.betting_state.last_raise_increment
            == raise_increment
        )

    def test_raise_resets_multiple_acted_players_to_needs_action(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        raise_increment = ChipAmount(50)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        acted_player_1 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        acted_player_2 = sample_player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, acted_player_1, acted_player_2],
            last_raise_increment=BIG_BLIND_STANDARD,
        )
        action = Action(action_type=ActionType.RAISE, amount=raise_increment)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_acted_player_1 = updated_game.get_player_by_id(
            acted_player_1.id
        )
        assert updated_acted_player_1 is not None
        assert (
            updated_acted_player_1.betting_status
            == BettingRoundActionStatus.NEEDS_ACTION
        )

        updated_acted_player_2 = updated_game.get_player_by_id(
            acted_player_2.id
        )
        assert updated_acted_player_2 is not None
        assert (
            updated_acted_player_2.betting_status
            == BettingRoundActionStatus.NEEDS_ACTION
        )


class TestAllInAction:
    """Tests for ALL_IN action application."""

    def test_all_in_sets_player_remaining_chips_to_zero(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        all_in_amount = ChipAmount(150)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=all_in_amount,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.ALL_IN, amount=all_in_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.remaining_chips == ChipAmount(0)

    def test_all_in_increases_total_invested_this_hand_by_all_in_amount(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        initial_invested = ChipAmount(20)
        all_in_amount = ChipAmount(150)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=all_in_amount,
            total_invested_this_hand=initial_invested,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.ALL_IN, amount=all_in_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.total_invested_this_hand == ChipAmount(170)

    def test_all_in_sets_player_betting_status_to_acted(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        all_in_amount = ChipAmount(150)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=all_in_amount,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.ALL_IN, amount=all_in_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.betting_status == BettingRoundActionStatus.ACTED

    def test_all_in_as_call_does_not_reset_other_players_betting_status(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        all_in_amount = ChipAmount(150)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=all_in_amount,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=all_in_amount,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.ALL_IN, amount=all_in_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert (
            updated_other_player.betting_status
            == BettingRoundActionStatus.ACTED
        )

    def test_all_in_as_raise_resets_other_players_betting_status(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        all_in_amount = ChipAmount(200)
        call_amount = ChipAmount(150)
        expected_raise_increment = ChipAmount(50)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=all_in_amount,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=call_amount,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.ALL_IN, amount=all_in_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert (
            updated_other_player.betting_status
            == BettingRoundActionStatus.NEEDS_ACTION
        )
        assert (
            updated_game.betting_state.last_raise_increment
            == expected_raise_increment
        )

    def test_all_in_when_player_has_already_invested_some_chips(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        initial_invested = ChipAmount(50)
        remaining_chips = ChipAmount(100)
        all_in_amount = remaining_chips
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=remaining_chips,
            total_invested_this_hand=initial_invested,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.ALL_IN, amount=all_in_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.remaining_chips == ChipAmount(0)
        assert updated_player.total_invested_this_hand == ChipAmount(150)

    def test_all_in_when_all_in_amount_equals_call_amount_treated_as_call_does_not_reopen(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        call_amount = ChipAmount(150)
        all_in_amount = call_amount
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=all_in_amount,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=call_amount,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.ALL_IN, amount=all_in_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert (
            updated_other_player.betting_status
            == BettingRoundActionStatus.ACTED
        )
        assert updated_game.betting_state.last_raise_increment == ChipAmount(0)

    def test_all_in_when_raise_increment_less_than_minimum_treated_as_call_does_not_reopen(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        call_amount = ChipAmount(100)
        minimum_raise_increment = ChipAmount(50)
        all_in_amount = ChipAmount(140)
        raise_increment = all_in_amount - call_amount
        assert raise_increment.value < minimum_raise_increment.value
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=all_in_amount,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=all_in_amount,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, other_player],
            last_raise_increment=minimum_raise_increment,
        )
        action = Action(action_type=ActionType.ALL_IN, amount=all_in_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert (
            updated_other_player.betting_status
            == BettingRoundActionStatus.ACTED
        )
        assert (
            updated_game.betting_state.last_raise_increment
            == minimum_raise_increment
        )

    def test_all_in_when_raise_increment_equals_minimum_treated_as_raise_reopens_action(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        call_amount = ChipAmount(100)
        minimum_raise_increment = ChipAmount(50)
        all_in_amount = ChipAmount(150)
        raise_increment = all_in_amount - call_amount
        assert raise_increment.value == minimum_raise_increment.value
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=all_in_amount,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=call_amount,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, other_player],
            last_raise_increment=minimum_raise_increment,
        )
        action = Action(action_type=ActionType.ALL_IN, amount=all_in_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert (
            updated_other_player.betting_status
            == BettingRoundActionStatus.NEEDS_ACTION
        )
        assert (
            updated_game.betting_state.last_raise_increment == raise_increment
        )

    def test_all_in_when_raise_increment_greater_than_minimum_treated_as_raise_reopens_action(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        call_amount = ChipAmount(100)
        minimum_raise_increment = ChipAmount(50)
        all_in_amount = ChipAmount(200)
        raise_increment = all_in_amount - call_amount
        assert raise_increment.value > minimum_raise_increment.value
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=all_in_amount,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=call_amount,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, other_player],
            last_raise_increment=minimum_raise_increment,
        )
        action = Action(action_type=ActionType.ALL_IN, amount=all_in_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert (
            updated_other_player.betting_status
            == BettingRoundActionStatus.NEEDS_ACTION
        )
        assert (
            updated_game.betting_state.last_raise_increment == raise_increment
        )

    def test_all_in_for_exact_call_amount_less_than_big_blind_does_not_reopen(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Per rule book 7.9.7: All-in that exactly matches the call amount is a call, not raise.

        Scenario: Current bet is 10, player has 10 chips, goes all-in for 10.
        This is a call (not a raise) so betting should NOT reopen.
        """
        call_amount = ChipAmount(10)
        assert call_amount.value < BIG_BLIND_STANDARD.value
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=call_amount,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=call_amount,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.ALL_IN, amount=call_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert (
            updated_other_player.betting_status
            == BettingRoundActionStatus.ACTED
        )
        assert updated_game.betting_state.last_raise_increment == ChipAmount(0)

    def test_all_in_when_no_call_amount_and_all_in_equals_big_blind_treated_as_raise_reopens_action(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        all_in_amount = BIG_BLIND_STANDARD
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=all_in_amount,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.ALL_IN, amount=all_in_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert (
            updated_other_player.betting_status
            == BettingRoundActionStatus.NEEDS_ACTION
        )
        assert updated_game.betting_state.last_raise_increment == all_in_amount

    def test_all_in_bb_option_for_less_than_minimum_raise_still_requires_action(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Per rule book 8.3: BB option all-in for less than min raise still requires call/fold.

        Scenario: Preflop, everyone limps to BB (20). BB has only 5 chips remaining.
        BB goes all-in for 5 (raise_amount = 5, minimum_raise = 20).

        Per rule book 8.3: "not reopening" means players cannot RE-RAISE, but they
        still must call or fold to match the new bet level. The limper has only
        invested 20, but BB has invested 25 - limper needs to call 5 or fold.

        Rule book quote: "It does NOT reopen betting to players who have already acted"
        This means players cannot RE-RAISE, not that they don't need to act at all.
        """
        bb_invested = BIG_BLIND_STANDARD
        all_in_amount = ChipAmount(5)
        assert all_in_amount.value < BIG_BLIND_STANDARD.value
        bb_player = sample_player_factory(
            player_id="bb-player",
            seat=Seat.SEAT_0,
            remaining_chips=all_in_amount,
            total_invested_this_hand=bb_invested,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        limper = sample_player_factory(
            player_id="limper",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=bb_invested,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([bb_player, limper])
        action = Action(action_type=ActionType.ALL_IN, amount=all_in_amount)

        updated_game = ActionApplier.apply_action(game, bb_player.id, action)

        # Limper needs to act (call 5 or fold) because they haven't matched the new level
        updated_limper = updated_game.get_player_by_id(limper.id)
        assert updated_limper is not None
        assert (
            updated_limper.betting_status
            == BettingRoundActionStatus.NEEDS_ACTION
        )
        # Limper cannot re-raise (WSOP Rule 96: short all-in doesn't reopen betting)
        assert updated_limper.can_raise is False
        # last_raise_increment is NOT updated because this is not a legal raise
        # (preserves the minimum raise requirement for future legal raises)
        assert updated_game.betting_state.last_raise_increment == ChipAmount(0)


class TestBetAction:
    """Tests for BET action application."""

    def test_bet_reduces_player_chips_by_bet_amount(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        initial_chips = ChipAmount(200)
        bet_amount = ChipAmount(50)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=initial_chips,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        game.hand_state.current_phase = HandPhase.FLOP
        action = Action(action_type=ActionType.BET, amount=bet_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.remaining_chips == ChipAmount(150)

    def test_bet_increases_total_invested_this_hand_by_bet_amount(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        initial_invested = ChipAmount(0)
        bet_amount = ChipAmount(50)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=initial_invested,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        game.hand_state.current_phase = HandPhase.FLOP
        action = Action(action_type=ActionType.BET, amount=bet_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.total_invested_this_hand == bet_amount

    def test_bet_sets_player_betting_status_to_acted(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        bet_amount = ChipAmount(50)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        game.hand_state.current_phase = HandPhase.FLOP
        action = Action(action_type=ActionType.BET, amount=bet_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.betting_status == BettingRoundActionStatus.ACTED

    def test_bet_resets_other_acted_players_to_needs_action(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        bet_amount = ChipAmount(50)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        game.hand_state.current_phase = HandPhase.FLOP
        action = Action(action_type=ActionType.BET, amount=bet_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert (
            updated_other_player.betting_status
            == BettingRoundActionStatus.NEEDS_ACTION
        )

    def test_bet_updates_betting_state_last_raise_increment_to_bet_amount(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        bet_amount = ChipAmount(50)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        game.hand_state.current_phase = HandPhase.FLOP
        action = Action(action_type=ActionType.BET, amount=bet_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        assert updated_game.betting_state.last_raise_increment == bet_amount

    def test_bet_with_minimum_bet_amount_big_blind(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        bet_amount = BIG_BLIND_STANDARD
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        game.hand_state.current_phase = HandPhase.FLOP
        action = Action(action_type=ActionType.BET, amount=bet_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.remaining_chips == ChipAmount(180)
        assert updated_game.betting_state.last_raise_increment == bet_amount

    def test_bet_with_maximum_bet_amount_all_chips(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        all_chips = ChipAmount(200)
        bet_amount = all_chips
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=all_chips,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        game.hand_state.current_phase = HandPhase.FLOP
        action = Action(action_type=ActionType.BET, amount=bet_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.remaining_chips == ChipAmount(0)
        assert updated_game.betting_state.last_raise_increment == bet_amount

    def test_bet_does_not_reset_folded_players(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        bet_amount = ChipAmount(50)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        acted_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        folded_player = sample_player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=LARGE_CHIPS,
            participation_status=HandParticipationStatus.FOLDED,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, acted_player, folded_player])
        game.hand_state.current_phase = HandPhase.FLOP
        action = Action(action_type=ActionType.BET, amount=bet_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_folded_player = updated_game.get_player_by_id(folded_player.id)
        assert updated_folded_player is not None
        assert (
            updated_folded_player.betting_status
            == BettingRoundActionStatus.ACTED
        )

    def test_bet_resets_multiple_acted_players_to_needs_action(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        bet_amount = ChipAmount(50)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        acted_player_1 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        acted_player_2 = sample_player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, acted_player_1, acted_player_2])
        game.hand_state.current_phase = HandPhase.FLOP
        action = Action(action_type=ActionType.BET, amount=bet_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_acted_player_1 = updated_game.get_player_by_id(
            acted_player_1.id
        )
        assert updated_acted_player_1 is not None
        assert (
            updated_acted_player_1.betting_status
            == BettingRoundActionStatus.NEEDS_ACTION
        )

        updated_acted_player_2 = updated_game.get_player_by_id(
            acted_player_2.id
        )
        assert updated_acted_player_2 is not None
        assert (
            updated_acted_player_2.betting_status
            == BettingRoundActionStatus.NEEDS_ACTION
        )

    def test_bet_works_on_flop_turn_and_river(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        bet_amount = ChipAmount(50)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.ACTED,
        )

        for phase in [HandPhase.FLOP, HandPhase.TURN, HandPhase.RIVER]:
            game = minimal_game_factory([player, other_player])
            game.hand_state.current_phase = phase
            action = Action(action_type=ActionType.BET, amount=bet_amount)

            updated_game = ActionApplier.apply_action(game, player.id, action)

            updated_player = updated_game.get_player_by_id(player.id)
            assert updated_player is not None
            assert updated_player.remaining_chips == ChipAmount(150)
            assert (
                updated_game.betting_state.last_raise_increment == bet_amount
            )


class TestActionValidation:
    """Tests for action validation logic in ActionApplier."""

    def test_raises_error_when_bet_amount_below_minimum(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        game.hand_state.current_phase = HandPhase.FLOP
        bet_amount = ChipAmount(10)
        assert bet_amount.value < BIG_BLIND_STANDARD.value
        action = Action(action_type=ActionType.BET, amount=bet_amount)

        with pytest.raises(ValueError, match="Bet amount .* is below minimum"):
            ActionApplier.apply_action(game, player.id, action)

    def test_raises_error_when_bet_amount_above_maximum(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(50),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        game.hand_state.current_phase = HandPhase.FLOP
        bet_amount = ChipAmount(100)
        assert bet_amount.value > player.remaining_chips.value
        action = Action(action_type=ActionType.BET, amount=bet_amount)

        with pytest.raises(ValueError, match="Bet amount .* exceeds maximum"):
            ActionApplier.apply_action(game, player.id, action)

    def test_raises_error_when_all_in_amount_does_not_match_remaining_chips(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        remaining_chips = ChipAmount(150)
        incorrect_amount = ChipAmount(100)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=remaining_chips,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.ALL_IN, amount=incorrect_amount)

        with pytest.raises(
            ValueError, match="All-in amount .* does not match"
        ):
            ActionApplier.apply_action(game, player.id, action)

    def test_raises_error_when_action_type_not_available(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        game.hand_state.current_phase = HandPhase.FLOP
        action = Action(action_type=ActionType.RAISE, amount=ChipAmount(50))

        with pytest.raises(ValueError, match="Action raise is not available"):
            ActionApplier.apply_action(game, player.id, action)

    def test_raises_error_when_raise_amount_below_minimum(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Per rule book 7.9.6: Raise must be at least the minimum raise increment."""
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, other_player], last_raise_increment=ChipAmount(30)
        )
        raise_amount = ChipAmount(10)
        assert raise_amount.value < ChipAmount(30).value
        action = Action(action_type=ActionType.RAISE, amount=raise_amount)

        with pytest.raises(
            ValueError, match="Raise amount .* is below minimum"
        ):
            ActionApplier.apply_action(game, player.id, action)

    def test_raises_error_when_raise_amount_above_maximum(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Per rule book 7.9.6: Maximum raise is player's remaining chips after call."""
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, other_player], last_raise_increment=BIG_BLIND_STANDARD
        )
        max_raise = ChipAmount(70)
        raise_amount = ChipAmount(100)
        assert raise_amount.value > max_raise.value
        action = Action(action_type=ActionType.RAISE, amount=raise_amount)

        with pytest.raises(
            ValueError, match="Raise amount .* exceeds maximum"
        ):
            ActionApplier.apply_action(game, player.id, action)


class TestNextPlayerCalculation:
    """Tests for finding next player who needs action."""

    def test_finds_next_player_when_sequential_players_need_action(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        player3 = sample_player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player1, player2, player3])
        game.betting_state.position_to_act = 0
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player1.id, action)

        assert updated_game.betting_state.position_to_act == 1

    def test_wraps_around_to_first_player_when_last_player_acts(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        game = minimal_game_factory([player1, player2])
        game.betting_state.position_to_act = 1
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player2.id, action)

        assert updated_game.betting_state.position_to_act == NO_POSITION_TO_ACT

    def test_returns_none_when_no_players_need_action(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player1, player2])
        game.betting_state.position_to_act = 0
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player1.id, action)

        assert updated_game.betting_state.position_to_act == NO_POSITION_TO_ACT

    def test_skips_folded_players_when_finding_next_player(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        folded_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            participation_status=HandParticipationStatus.FOLDED,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        player3 = sample_player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        game = minimal_game_factory([player1, folded_player, player3])
        game.betting_state.position_to_act = 0
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player1.id, action)

        assert updated_game.betting_state.position_to_act == 2

    def test_skips_players_who_have_already_acted_when_finding_next_player(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        acted_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        player3 = sample_player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        game = minimal_game_factory([player1, acted_player, player3])
        game.betting_state.position_to_act = 0
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player1.id, action)

        assert updated_game.betting_state.position_to_act == 2

    def test_finds_next_player_after_raise_resets_other_players(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player1, player2], last_raise_increment=BIG_BLIND_STANDARD
        )
        game.betting_state.position_to_act = 0
        action = Action(action_type=ActionType.RAISE, amount=ChipAmount(50))

        updated_game = ActionApplier.apply_action(game, player1.id, action)

        assert updated_game.betting_state.position_to_act == 1


class TestGameStatePreservation:
    """Tests that game state is properly preserved and updated."""

    def test_returns_new_game_instance_does_not_mutate_original(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        original_player_chips = player.remaining_chips
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        assert updated_game is not game
        assert player.remaining_chips == original_player_chips

    def test_preserves_game_identity_after_action(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        assert updated_game.identity == game.identity

    def test_preserves_tournament_config_after_action(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        assert updated_game.tournament_config == game.tournament_config

    def test_preserves_hand_state_after_action(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        assert updated_game.hand_state == game.hand_state

    def test_pot_state_calculated_from_investments_after_action(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        total_invested = BIG_BLIND_STANDARD.value * 2
        assert updated_game.pot_state.main_pot.amount.value == total_invested

    def test_preserves_button_seat_after_action(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        assert updated_game.button_seat == game.button_seat

    def test_preserves_blind_state_after_action(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        assert updated_game.blind_state == game.blind_state

    def test_preserves_results_after_action(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        assert updated_game.outcome == game.outcome


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_fold_when_player_has_hole_cards_preserves_them(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        hole_cards = make_hand(
            make_card(rank=Rank.ACE, suit=Suit.SPADES),
            make_card(rank=Rank.KING, suit=Suit.HEARTS),
        )
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
            hole_cards=hole_cards,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.FOLD)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.hole_cards == hole_cards

    def test_call_when_player_has_exactly_call_amount_chips(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        call_amount = ChipAmount(30)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=call_amount,
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.CALL)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.remaining_chips == ChipAmount(0)
        assert updated_player.total_invested_this_hand == ChipAmount(50)

    def test_raise_with_minimum_raise_increment(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        minimum_raise = BIG_BLIND_STANDARD
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, other_player], last_raise_increment=BIG_BLIND_STANDARD
        )
        action = Action(action_type=ActionType.RAISE, amount=minimum_raise)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_game.betting_state.last_raise_increment == minimum_raise

    def test_raise_with_maximum_raise_increment(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        max_raise = ChipAmount(170)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, other_player], last_raise_increment=BIG_BLIND_STANDARD
        )
        action = Action(action_type=ActionType.RAISE, amount=max_raise)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.remaining_chips == ChipAmount(0)
        assert updated_game.betting_state.last_raise_increment == max_raise

    def test_all_in_with_single_chip(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        all_in_amount = ChipAmount(1)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=all_in_amount,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.ALL_IN, amount=all_in_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.remaining_chips == ChipAmount(0)
        assert updated_player.total_invested_this_hand == ChipAmount(1)

    def test_all_in_when_player_has_already_invested_chips(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        initial_invested = ChipAmount(100)
        remaining_chips = ChipAmount(50)
        all_in_amount = remaining_chips
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=remaining_chips,
            total_invested_this_hand=initial_invested,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.ALL_IN, amount=all_in_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.remaining_chips == ChipAmount(0)
        assert updated_player.total_invested_this_hand == ChipAmount(150)

    def test_raise_does_not_reset_eliminated_players(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        raise_increment = ChipAmount(50)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        acted_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        eliminated_player = sample_player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=ChipAmount(0),
            participation_status=HandParticipationStatus.ELIMINATED,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, acted_player, eliminated_player],
            last_raise_increment=BIG_BLIND_STANDARD,
        )
        action = Action(action_type=ActionType.RAISE, amount=raise_increment)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_eliminated_player = updated_game.get_player_by_id(
            eliminated_player.id
        )
        assert updated_eliminated_player is not None
        assert (
            updated_eliminated_player.betting_status
            == BettingRoundActionStatus.ACTED
        )


class TestInputValidation:
    """Tests for input validation and error handling."""

    def test_raises_error_when_player_not_found(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Applying action to non-existent player should raise ValueError."""
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=LARGE_CHIPS,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.FOLD)

        with pytest.raises(ValueError, match="Player non-existent not found"):
            ActionApplier.apply_action(game, "non-existent", action)

    def test_raises_error_when_check_not_available(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Cannot check when facing a bet."""
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        bettor = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, bettor])
        action = Action(action_type=ActionType.CHECK)

        with pytest.raises(ValueError, match="check is not available"):
            ActionApplier.apply_action(game, player.id, action)

    def test_raises_error_when_call_not_available(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Cannot call when call amount is zero (should check instead)."""
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.CALL)

        with pytest.raises(ValueError, match="call is not available"):
            ActionApplier.apply_action(game, player.id, action)


class TestMultiPlayerScenarios:
    """Tests for 3+ player scenarios."""

    def test_three_player_fold_chain(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """In a 3-player game, if two players fold, the remaining player wins."""
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        player3 = sample_player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player1, player2, player3])

        # Player 1 folds
        updated_game = ActionApplier.apply_action(
            game, player1.id, Action(action_type=ActionType.FOLD)
        )

        # Verify player 1 is folded
        p1 = updated_game.get_player_by_id(player1.id)
        assert p1 is not None
        assert p1.participation_status == HandParticipationStatus.FOLDED

        # Players 2 and 3 should still be in hand
        p2 = updated_game.get_player_by_id(player2.id)
        p3 = updated_game.get_player_by_id(player3.id)
        assert (
            p2 is not None
            and p2.participation_status == HandParticipationStatus.IN_HAND
        )
        assert (
            p3 is not None
            and p3.participation_status == HandParticipationStatus.IN_HAND
        )

    def test_three_player_raise_resets_both_other_players(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """When one player raises, both other acted players should be reset to NEEDS_ACTION."""
        raiser = sample_player_factory(
            player_id="raiser",
            seat=Seat.SEAT_0,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        acted1 = sample_player_factory(
            player_id="acted-1",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        acted2 = sample_player_factory(
            player_id="acted-2",
            seat=Seat.SEAT_2,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [raiser, acted1, acted2], last_raise_increment=ChipAmount(30)
        )
        raise_amount = ChipAmount(50)
        call_amount = ChipAmount(30)  # 50 - 20 = 30

        updated_game = ActionApplier.apply_action(
            game,
            raiser.id,
            Action(action_type=ActionType.RAISE, amount=raise_amount),
        )

        # Both acted players should now need action
        p1 = updated_game.get_player_by_id(acted1.id)
        p2 = updated_game.get_player_by_id(acted2.id)
        assert (
            p1 is not None
            and p1.betting_status == BettingRoundActionStatus.NEEDS_ACTION
        )
        assert (
            p2 is not None
            and p2.betting_status == BettingRoundActionStatus.NEEDS_ACTION
        )

    def test_four_player_complex_action_sequence(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """4-player scenario: verify position_to_act updates correctly after each action."""
        p1 = sample_player_factory(
            player_id="p1",
            seat=Seat.SEAT_0,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        p2 = sample_player_factory(
            player_id="p2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        p3 = sample_player_factory(
            player_id="p3",
            seat=Seat.SEAT_2,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        p4 = sample_player_factory(
            player_id="p4",
            seat=Seat.SEAT_3,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        game = minimal_game_factory([p1, p2, p3, p4])

        # P1 checks (position should go to P2)
        game = ActionApplier.apply_action(
            game, p1.id, Action(action_type=ActionType.CHECK)
        )
        assert game.betting_state.position_to_act == 1  # P2's seat

        # P2 checks (position should go to P3)
        game = ActionApplier.apply_action(
            game, p2.id, Action(action_type=ActionType.CHECK)
        )
        assert game.betting_state.position_to_act == 2  # P3's seat

        # P3 checks (position should go to P4)
        game = ActionApplier.apply_action(
            game, p3.id, Action(action_type=ActionType.CHECK)
        )
        assert game.betting_state.position_to_act == 3  # P4's seat

        # P4 checks (round complete, no position to act)
        game = ActionApplier.apply_action(
            game, p4.id, Action(action_type=ActionType.CHECK)
        )
        assert game.betting_state.position_to_act == NO_POSITION_TO_ACT

    def test_five_player_with_varying_investments(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """5-player scenario with different investment levels."""
        players = [
            sample_player_factory(
                player_id=f"p{i}",
                seat=Seat(i),
                remaining_chips=LARGE_CHIPS,
                total_invested_this_hand=ChipAmount(
                    i * 10 + 20
                ),  # 20, 30, 40, 50, 60
                betting_status=(
                    BettingRoundActionStatus.ACTED
                    if i == 4
                    else BettingRoundActionStatus.NEEDS_ACTION
                ),
            )
            for i in range(5)
        ]
        game = minimal_game_factory(
            players, last_raise_increment=ChipAmount(10)
        )

        # Player 0 (invested 20) needs to call 40 to match highest (60)
        # Players 1, 2, 3 also need to call (30, 20, 10 respectively)
        # Only player 4 (invested 60) has already matched
        updated_game = ActionApplier.apply_action(
            game, players[0].id, Action(action_type=ActionType.CALL)
        )

        p0 = updated_game.get_player_by_id(players[0].id)
        assert p0 is not None
        assert p0.total_invested_this_hand == ChipAmount(60)
        assert p0.betting_status == BettingRoundActionStatus.ACTED

        # After player 0 calls, action should move to player 1 (seat 1)
        assert updated_game.betting_state.position_to_act == 1

    def test_multiple_all_ins_at_different_levels(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Test scenario with multiple players going all-in at different stack sizes."""
        # Player 1: 50 chips, already all-in
        # Player 2: 100 chips
        # Player 3: 200 chips
        p1 = sample_player_factory(
            player_id="p1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        p2 = sample_player_factory(
            player_id="p2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        p3 = sample_player_factory(
            player_id="p3",
            seat=Seat.SEAT_2,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [p1, p2, p3], last_raise_increment=ChipAmount(50)
        )

        # P2 goes all-in for 100
        updated_game = ActionApplier.apply_action(
            game,
            p2.id,
            Action(action_type=ActionType.ALL_IN, amount=ChipAmount(100)),
        )

        # P2 should now be all-in
        p2_updated = updated_game.get_player_by_id(p2.id)
        assert p2_updated is not None
        assert p2_updated.remaining_chips == ChipAmount(0)
        assert p2_updated.total_invested_this_hand == ChipAmount(100)

        # P3 should need to act (since 100 >= min raise of 50)
        p3_updated = updated_game.get_player_by_id(p3.id)
        assert p3_updated is not None
        assert (
            p3_updated.betting_status == BettingRoundActionStatus.NEEDS_ACTION
        )


class TestBoundaryConditions:
    """Tests for exact boundary values and edge cases."""

    def test_bet_exactly_minimum_amount(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Betting exactly the minimum (BB) should succeed."""
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other])
        game.hand_state.current_phase = HandPhase.FLOP

        updated_game = ActionApplier.apply_action(
            game,
            player.id,
            Action(action_type=ActionType.BET, amount=BIG_BLIND_STANDARD),
        )

        p = updated_game.get_player_by_id(player.id)
        assert p is not None
        assert p.total_invested_this_hand == BIG_BLIND_STANDARD

    def test_bet_one_below_minimum_fails(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Betting one below minimum should fail."""
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other])
        game.hand_state.current_phase = HandPhase.FLOP
        bet_amount = ChipAmount(BIG_BLIND_STANDARD.value - 1)

        with pytest.raises(ValueError, match="below minimum"):
            ActionApplier.apply_action(
                game,
                player.id,
                Action(action_type=ActionType.BET, amount=bet_amount),
            )

    def test_raise_exactly_minimum_increment(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Raising exactly the minimum increment should succeed."""
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        bettor = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, bettor], last_raise_increment=ChipAmount(50)
        )
        # Minimum raise is max(last_raise, BB) = max(50, 20) = 50

        updated_game = ActionApplier.apply_action(
            game,
            player.id,
            Action(action_type=ActionType.RAISE, amount=ChipAmount(50)),
        )

        p = updated_game.get_player_by_id(player.id)
        assert p is not None
        # Player should have called 50 + raised 50 = 100 total
        assert p.total_invested_this_hand == ChipAmount(100)

    def test_raise_one_below_minimum_increment_fails(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Raising one below minimum increment should fail."""
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        bettor = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, bettor], last_raise_increment=ChipAmount(50)
        )
        # Minimum raise is 50, raising 49 should fail

        with pytest.raises(ValueError, match="below minimum"):
            ActionApplier.apply_action(
                game,
                player.id,
                Action(action_type=ActionType.RAISE, amount=ChipAmount(49)),
            )

    def test_call_with_exactly_call_amount_chips(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Player with exactly the call amount can call."""
        call_amount = ChipAmount(50)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=call_amount,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        bettor = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=call_amount,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, bettor])

        updated_game = ActionApplier.apply_action(
            game, player.id, Action(action_type=ActionType.CALL)
        )

        p = updated_game.get_player_by_id(player.id)
        assert p is not None
        assert p.remaining_chips == ChipAmount(0)
        assert p.total_invested_this_hand == call_amount

    def test_player_with_one_chip_facing_large_bet(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Player with 1 chip facing 100 chip bet can only fold or all-in."""
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(1),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        bettor = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(100),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, bettor])

        # Should be able to go all-in for 1 chip
        updated_game = ActionApplier.apply_action(
            game,
            player.id,
            Action(action_type=ActionType.ALL_IN, amount=ChipAmount(1)),
        )

        p = updated_game.get_player_by_id(player.id)
        assert p is not None
        assert p.remaining_chips == ChipAmount(0)
        assert p.total_invested_this_hand == ChipAmount(1)


class TestPreFlopVsPostFlopRules:
    """Tests for preflop vs postflop action availability differences."""

    def test_bet_not_available_preflop(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """BET action is not available preflop (use RAISE instead)."""
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other])
        # Game is preflop by default

        with pytest.raises(
            ValueError, match="(?i)action bet is not available"
        ):
            ActionApplier.apply_action(
                game,
                player.id,
                Action(action_type=ActionType.BET, amount=ChipAmount(50)),
            )

    def test_raise_available_preflop_when_call_amount_is_zero(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """RAISE is available preflop even when call_amount=0 (BB option)."""
        bb_player = sample_player_factory(
            player_id="bb",
            seat=Seat.SEAT_0,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        limper = sample_player_factory(
            player_id="limper",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([bb_player, limper])

        # BB can raise (not bet) even when call_amount is 0
        updated_game = ActionApplier.apply_action(
            game,
            bb_player.id,
            Action(action_type=ActionType.RAISE, amount=BIG_BLIND_STANDARD),
        )

        p = updated_game.get_player_by_id(bb_player.id)
        assert p is not None
        assert p.total_invested_this_hand == ChipAmount(40)  # 20 + 20 raise

    def test_bet_available_postflop_first_to_act(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """BET is available postflop when first to act."""
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other])
        game.hand_state.current_phase = HandPhase.FLOP

        updated_game = ActionApplier.apply_action(
            game,
            player.id,
            Action(action_type=ActionType.BET, amount=BIG_BLIND_STANDARD),
        )

        p = updated_game.get_player_by_id(player.id)
        assert p is not None
        assert p.total_invested_this_hand == BIG_BLIND_STANDARD

    def test_raise_available_postflop_when_facing_bet(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """RAISE is available postflop when facing a bet."""
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        bettor = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, bettor], last_raise_increment=ChipAmount(50)
        )
        game.hand_state.current_phase = HandPhase.FLOP

        updated_game = ActionApplier.apply_action(
            game,
            player.id,
            Action(action_type=ActionType.RAISE, amount=ChipAmount(50)),
        )

        p = updated_game.get_player_by_id(player.id)
        assert p is not None
        assert p.total_invested_this_hand == ChipAmount(
            100
        )  # call 50 + raise 50


class TestRaiseSequences:
    """Tests for sequences of raises."""

    def test_last_raise_increment_updates_on_each_raise(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Each raise should update last_raise_increment to the raise amount."""
        p1 = sample_player_factory(
            player_id="p1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(500),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        p2 = sample_player_factory(
            player_id="p2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(500),
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [p1, p2], last_raise_increment=ChipAmount(50)
        )

        # P1 raises 50 (call 50 + raise 50 = 100 total)
        game = ActionApplier.apply_action(
            game,
            p1.id,
            Action(action_type=ActionType.RAISE, amount=ChipAmount(50)),
        )
        assert game.betting_state.last_raise_increment == ChipAmount(50)

        # P2 now needs to act, reraises 100 (call 50 + raise 100 = 200 total)
        game = ActionApplier.apply_action(
            game,
            p2.id,
            Action(action_type=ActionType.RAISE, amount=ChipAmount(100)),
        )
        assert game.betting_state.last_raise_increment == ChipAmount(100)

    def test_minimum_raise_uses_previous_raise_size(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """After a 100 raise, next minimum raise is 100 (not BB)."""
        p1 = sample_player_factory(
            player_id="p1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(500),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        p2 = sample_player_factory(
            player_id="p2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(500),
            total_invested_this_hand=ChipAmount(100),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        # Last raise was 100, so minimum for P1's re-raise is 100
        game = minimal_game_factory(
            [p1, p2], last_raise_increment=ChipAmount(100)
        )

        # Raising 99 should fail (below minimum)
        with pytest.raises(ValueError, match="below minimum"):
            ActionApplier.apply_action(
                game,
                p1.id,
                Action(action_type=ActionType.RAISE, amount=ChipAmount(99)),
            )

        # Raising exactly 100 should succeed
        updated_game = ActionApplier.apply_action(
            game,
            p1.id,
            Action(action_type=ActionType.RAISE, amount=ChipAmount(100)),
        )
        p1_updated = updated_game.get_player_by_id(p1.id)
        assert p1_updated is not None
        assert p1_updated.total_invested_this_hand == ChipAmount(
            200
        )  # 100 call + 100 raise


class TestPlayerStateConsistency:
    """Tests to verify player state consistency after actions."""

    def test_chips_never_go_negative(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Player chips should never go negative after any action."""
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(30),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        bettor = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(100),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, bettor])

        # When player cannot afford to call, CALL is not available
        # Use ALL_IN instead, which should result in 0 chips, not negative
        updated_game = ActionApplier.apply_action(
            game,
            player.id,
            Action(
                action_type=ActionType.ALL_IN, amount=player.remaining_chips
            ),
        )

        p = updated_game.get_player_by_id(player.id)
        assert p is not None
        assert p.remaining_chips.value == 0

    def test_total_invested_never_decreases(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Total invested should only increase, never decrease."""
        initial_invested = ChipAmount(50)
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=initial_invested,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=initial_invested,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other])

        # Check should not decrease investment
        updated_game = ActionApplier.apply_action(
            game, player.id, Action(action_type=ActionType.CHECK)
        )

        p = updated_game.get_player_by_id(player.id)
        assert p is not None
        assert p.total_invested_this_hand == initial_invested

    def test_only_fold_changes_participation_status(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Only FOLD should change participation_status from IN_HAND."""
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other])

        # Check should not change participation status
        updated_game = ActionApplier.apply_action(
            game, player.id, Action(action_type=ActionType.CHECK)
        )
        p = updated_game.get_player_by_id(player.id)
        assert p is not None
        assert p.participation_status == HandParticipationStatus.IN_HAND

    def test_only_fold_clears_hole_cards(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Only FOLD should clear hole cards."""
        hole_cards = make_hand(
            make_card(Rank.ACE, Suit.SPADES), make_card(Rank.KING, Suit.SPADES)
        )
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
            hole_cards=hole_cards,
        )
        other = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=BIG_BLIND_STANDARD,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other])

        # Check should not clear hole cards
        updated_game = ActionApplier.apply_action(
            game, player.id, Action(action_type=ActionType.CHECK)
        )
        p = updated_game.get_player_by_id(player.id)
        assert p is not None
        assert p.hole_cards is not None
        assert p.hole_cards == hole_cards


class TestAllInCanRaiseFlag:
    """Tests for can_raise flag behavior per Rule 8.3 / WSOP Rule 96."""

    def test_short_all_in_facing_bet_sets_can_raise_false(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Short all-in (< min raise) sets acted players' can_raise=False."""
        # Setup: call=100, min_raise=50, all_in=130 (increment=30 < min=50)
        call_amount = ChipAmount(100)
        minimum_raise_increment = ChipAmount(50)
        all_in_amount = ChipAmount(130)
        raise_increment = all_in_amount - call_amount
        assert raise_increment.value < minimum_raise_increment.value

        player = sample_player_factory(
            player_id="short-stack",
            seat=Seat.SEAT_0,
            remaining_chips=all_in_amount,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="big-stack",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=call_amount,
            betting_status=BettingRoundActionStatus.ACTED,
            can_raise=True,
        )
        game = minimal_game_factory(
            [player, other_player],
            last_raise_increment=minimum_raise_increment,
        )
        action = Action(action_type=ActionType.ALL_IN, amount=all_in_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert (
            updated_other_player.betting_status
            == BettingRoundActionStatus.NEEDS_ACTION
        )
        assert updated_other_player.can_raise is False

    def test_short_all_in_postflop_no_bet_sets_can_raise_false(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Postflop all-in < BB when no bet exists sets can_raise=False."""
        # call_amount=0, all_in=10 (< BB=20)
        all_in_amount = ChipAmount(10)
        assert all_in_amount.value < BIG_BLIND_STANDARD.value

        player = sample_player_factory(
            player_id="short-stack",
            seat=Seat.SEAT_0,
            remaining_chips=all_in_amount,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="big-stack",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.ACTED,
            can_raise=True,
        )
        game = minimal_game_factory([player, other_player])
        game.hand_state.current_phase = HandPhase.FLOP
        action = Action(action_type=ActionType.ALL_IN, amount=all_in_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert (
            updated_other_player.betting_status
            == BettingRoundActionStatus.NEEDS_ACTION
        )
        assert updated_other_player.can_raise is False

    def test_legal_all_in_raise_sets_can_raise_true(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Legal all-in raise (>= min raise) sets can_raise=True."""
        # call=100, min_raise=50, all_in=150 (increment=50 >= min=50)
        call_amount = ChipAmount(100)
        minimum_raise_increment = ChipAmount(50)
        all_in_amount = ChipAmount(150)
        raise_increment = all_in_amount - call_amount
        assert raise_increment.value >= minimum_raise_increment.value

        player = sample_player_factory(
            player_id="raiser",
            seat=Seat.SEAT_0,
            remaining_chips=all_in_amount,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="big-stack",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=call_amount,
            betting_status=BettingRoundActionStatus.ACTED,
            can_raise=True,
        )
        game = minimal_game_factory(
            [player, other_player],
            last_raise_increment=minimum_raise_increment,
        )
        action = Action(action_type=ActionType.ALL_IN, amount=all_in_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert (
            updated_other_player.betting_status
            == BettingRoundActionStatus.NEEDS_ACTION
        )
        assert updated_other_player.can_raise is True

    def test_legal_raise_after_short_all_in_restores_can_raise_true(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Legal raise resets can_raise=True for players blocked by short all-in."""
        # Player A: can_raise=False from short all-in
        # Player B: makes legal raise
        # Player A: can_raise should be True now
        raise_increment = ChipAmount(50)
        player_blocked = sample_player_factory(
            player_id="blocked-player",
            seat=Seat.SEAT_0,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(100),
            betting_status=BettingRoundActionStatus.ACTED,
            can_raise=False,  # Blocked by previous short all-in
        )
        raiser = sample_player_factory(
            player_id="raiser",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(100),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
            can_raise=True,
        )
        game = minimal_game_factory(
            [player_blocked, raiser], last_raise_increment=BIG_BLIND_STANDARD
        )
        action = Action(action_type=ActionType.RAISE, amount=raise_increment)

        updated_game = ActionApplier.apply_action(game, raiser.id, action)

        updated_blocked_player = updated_game.get_player_by_id(
            player_blocked.id
        )
        assert updated_blocked_player is not None
        assert (
            updated_blocked_player.betting_status
            == BettingRoundActionStatus.NEEDS_ACTION
        )
        assert updated_blocked_player.can_raise is True

    def test_raise_does_not_reset_all_in_player_to_needs_action(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """All-in players (ACTED with 0 chips) stay ACTED after raises."""
        raise_increment = ChipAmount(50)
        all_in_player = sample_player_factory(
            player_id="all-in-player",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(100),
            betting_status=BettingRoundActionStatus.ACTED,
            participation_status=HandParticipationStatus.IN_HAND,
        )
        raiser = sample_player_factory(
            player_id="raiser",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(100),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        game = minimal_game_factory(
            [all_in_player, raiser], last_raise_increment=BIG_BLIND_STANDARD
        )
        action = Action(action_type=ActionType.RAISE, amount=raise_increment)

        updated_game = ActionApplier.apply_action(game, raiser.id, action)

        updated_all_in_player = updated_game.get_player_by_id(all_in_player.id)
        assert updated_all_in_player is not None
        # All-in player should NOT be reset to NEEDS_ACTION
        assert (
            updated_all_in_player.betting_status
            == BettingRoundActionStatus.ACTED
        )

    def test_short_all_in_does_not_reset_all_in_player(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Short all-in doesn't reset other all-in players."""
        # all_in_player stays ACTED even after short all-in
        all_in_player = sample_player_factory(
            player_id="all-in-player",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(100),
            betting_status=BettingRoundActionStatus.ACTED,
            participation_status=HandParticipationStatus.IN_HAND,
        )
        short_all_in_player = sample_player_factory(
            player_id="short-all-in",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(30),  # Short all-in of 30
            total_invested_this_hand=ChipAmount(100),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        game = minimal_game_factory(
            [all_in_player, short_all_in_player],
            last_raise_increment=ChipAmount(50),
        )
        action = Action(action_type=ActionType.ALL_IN, amount=ChipAmount(30))

        updated_game = ActionApplier.apply_action(
            game, short_all_in_player.id, action
        )

        updated_all_in_player = updated_game.get_player_by_id(all_in_player.id)
        assert updated_all_in_player is not None
        # All-in player should stay ACTED
        assert (
            updated_all_in_player.betting_status
            == BettingRoundActionStatus.ACTED
        )

    def test_three_player_short_all_in_affects_all_acted_players(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Short all-in sets can_raise=False for ALL acted players."""
        # P1 bets 100, P2 calls 100, P3 short all-in 130 -> both P1 and P2 get can_raise=False
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(100),
            betting_status=BettingRoundActionStatus.ACTED,
            can_raise=True,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(100),
            betting_status=BettingRoundActionStatus.ACTED,
            can_raise=True,
        )
        short_stack = sample_player_factory(
            player_id="short-stack",
            seat=Seat.SEAT_2,
            remaining_chips=ChipAmount(130),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        game = minimal_game_factory(
            [player1, player2, short_stack],
            last_raise_increment=ChipAmount(50),
        )
        action = Action(action_type=ActionType.ALL_IN, amount=ChipAmount(130))

        updated_game = ActionApplier.apply_action(game, short_stack.id, action)

        updated_player1 = updated_game.get_player_by_id(player1.id)
        updated_player2 = updated_game.get_player_by_id(player2.id)
        assert updated_player1 is not None
        assert updated_player2 is not None
        assert updated_player1.can_raise is False
        assert updated_player2.can_raise is False

    def test_needs_action_players_unaffected_by_short_all_in_can_raise(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Players who haven't acted yet keep can_raise=True after short all-in."""
        # P1 bets 100, P2 (not acted yet), P3 short all-in -> P2 keeps can_raise=True
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(100),
            betting_status=BettingRoundActionStatus.ACTED,
            can_raise=True,
        )
        player2_not_acted = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
            can_raise=True,
        )
        short_stack = sample_player_factory(
            player_id="short-stack",
            seat=Seat.SEAT_2,
            remaining_chips=ChipAmount(130),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        game = minimal_game_factory(
            [player1, player2_not_acted, short_stack],
            last_raise_increment=ChipAmount(50),
        )
        game.betting_state.position_to_act = 2  # Short stack to act
        action = Action(action_type=ActionType.ALL_IN, amount=ChipAmount(130))

        updated_game = ActionApplier.apply_action(game, short_stack.id, action)

        # Player1 who ACTED should have can_raise=False
        updated_player1 = updated_game.get_player_by_id(player1.id)
        assert updated_player1 is not None
        assert updated_player1.can_raise is False

        # Player2 who hasn't acted should keep can_raise=True
        updated_player2 = updated_game.get_player_by_id(player2_not_acted.id)
        assert updated_player2 is not None
        assert updated_player2.can_raise is True

    def test_all_in_exactly_equals_minimum_raise_sets_can_raise_true(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """All-in exactly equal to min raise is legal, sets can_raise=True."""
        # call=100, min_raise=50, all_in=150 -> exactly at boundary
        call_amount = ChipAmount(100)
        minimum_raise_increment = ChipAmount(50)
        all_in_amount = ChipAmount(150)

        player = sample_player_factory(
            player_id="all-in-player",
            seat=Seat.SEAT_0,
            remaining_chips=all_in_amount,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="other-player",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=call_amount,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, other_player],
            last_raise_increment=minimum_raise_increment,
        )
        action = Action(action_type=ActionType.ALL_IN, amount=all_in_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert updated_other_player.can_raise is True

    def test_all_in_one_chip_below_minimum_sets_can_raise_false(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """All-in one chip below min raise sets can_raise=False."""
        # call=100, min_raise=50, all_in=149 -> one below, can_raise=False
        call_amount = ChipAmount(100)
        minimum_raise_increment = ChipAmount(50)
        all_in_amount = ChipAmount(149)
        raise_increment = all_in_amount - call_amount
        assert raise_increment.value < minimum_raise_increment.value

        player = sample_player_factory(
            player_id="all-in-player",
            seat=Seat.SEAT_0,
            remaining_chips=all_in_amount,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="other-player",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=call_amount,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, other_player],
            last_raise_increment=minimum_raise_increment,
        )
        action = Action(action_type=ActionType.ALL_IN, amount=all_in_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert updated_other_player.can_raise is False


class TestLastRaiseIncrementPreservation:
    """Tests for last_raise_increment handling with short all-ins."""

    def test_short_all_in_preserves_last_raise_increment(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Short all-in does NOT update last_raise_increment."""
        # last_raise=50, short all-in should keep last_raise=50
        initial_last_raise = ChipAmount(50)
        call_amount = ChipAmount(100)
        all_in_amount = ChipAmount(130)  # Short all-in (increment=30 < min=50)

        player = sample_player_factory(
            player_id="short-stack",
            seat=Seat.SEAT_0,
            remaining_chips=all_in_amount,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="big-stack",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=call_amount,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, other_player], last_raise_increment=initial_last_raise
        )
        action = Action(action_type=ActionType.ALL_IN, amount=all_in_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        # last_raise_increment should be preserved (not updated)
        assert (
            updated_game.betting_state.last_raise_increment
            == initial_last_raise
        )

    def test_legal_all_in_updates_last_raise_increment(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Legal all-in DOES update last_raise_increment."""
        # last_raise=50, legal all-in of 200 (increment=100) should update to 100
        initial_last_raise = ChipAmount(50)
        call_amount = ChipAmount(100)
        all_in_amount = ChipAmount(
            200
        )  # Legal all-in (increment=100 >= min=50)
        expected_new_last_raise = all_in_amount - call_amount

        player = sample_player_factory(
            player_id="raiser",
            seat=Seat.SEAT_0,
            remaining_chips=all_in_amount,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="big-stack",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=call_amount,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, other_player], last_raise_increment=initial_last_raise
        )
        action = Action(action_type=ActionType.ALL_IN, amount=all_in_amount)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        # last_raise_increment should be updated
        assert (
            updated_game.betting_state.last_raise_increment
            == expected_new_last_raise
        )

    def test_call_preserves_last_raise_increment(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """CALL does not change last_raise_increment."""
        initial_last_raise = ChipAmount(50)

        player = sample_player_factory(
            player_id="caller",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="bettor",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, other_player], last_raise_increment=initial_last_raise
        )
        action = Action(action_type=ActionType.CALL)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        # last_raise_increment should be preserved
        assert (
            updated_game.betting_state.last_raise_increment
            == initial_last_raise
        )

    def test_fold_preserves_last_raise_increment(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """FOLD does not change last_raise_increment."""
        initial_last_raise = ChipAmount(50)

        player = sample_player_factory(
            player_id="folder",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="bettor",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, other_player], last_raise_increment=initial_last_raise
        )
        action = Action(action_type=ActionType.FOLD)

        updated_game = ActionApplier.apply_action(game, player.id, action)

        # last_raise_increment should be preserved
        assert (
            updated_game.betting_state.last_raise_increment
            == initial_last_raise
        )
