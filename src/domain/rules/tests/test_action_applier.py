"""Tests for ActionApplier - applies validated actions to game state."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from src.domain.models.actions import Action, ActionType
from src.domain.models.card import Rank, Suit
from src.domain.models.chips import ChipAmount
from src.domain.models.game import NO_CURRENT_PLAYER, Game, GamePhase
from src.domain.models.player import (BettingRoundActionStatus,
                                      HandParticipationStatus, Player)
from src.domain.models.seat import Seat
from src.domain.rules.action_applier import ActionApplier

from .conftest import (BIG_BLIND_STANDARD, LARGE_CHIPS, MEDIUM_CHIPS,
                       make_card, make_hand)


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

        updated_game = ActionApplier.apply_action(game, player, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.participation_status == HandParticipationStatus.FOLDED

    def test_fold_sets_player_betting_status_to_acted(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
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
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.FOLD)

        updated_game = ActionApplier.apply_action(game, player, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.betting_status == BettingRoundActionStatus.ACTED

    def test_fold_clears_player_hole_cards(
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
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        player.hole_cards = hole_cards
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.FOLD)

        updated_game = ActionApplier.apply_action(game, player, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.hole_cards is None

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

        updated_game = ActionApplier.apply_action(game, player, action)

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
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.FOLD)

        updated_game = ActionApplier.apply_action(game, player, action)

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

        updated_game = ActionApplier.apply_action(game, player, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert updated_other_player.betting_status == BettingRoundActionStatus.ACTED

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
        game = minimal_game_factory([player, other_player], last_raise_increment=raise_increment)
        action = Action(action_type=ActionType.FOLD)

        updated_game = ActionApplier.apply_action(game, player, action)

        assert updated_game.betting_state.last_raise_increment == raise_increment


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
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player, action)

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
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player, action)

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

        updated_game = ActionApplier.apply_action(game, player, action)

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
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.participation_status == HandParticipationStatus.IN_HAND

    def test_check_does_not_reset_other_players_betting_status(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
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
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert updated_other_player.betting_status == BettingRoundActionStatus.ACTED

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
        game = minimal_game_factory([player, other_player], last_raise_increment=raise_increment)
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player, action)

        assert updated_game.betting_state.last_raise_increment == raise_increment


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

        updated_game = ActionApplier.apply_action(game, player, action)

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

        updated_game = ActionApplier.apply_action(game, player, action)

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

        updated_game = ActionApplier.apply_action(game, player, action)

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

        updated_game = ActionApplier.apply_action(game, player, action)

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

        updated_game = ActionApplier.apply_action(game, player, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert updated_other_player.betting_status == BettingRoundActionStatus.ACTED

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
        game = minimal_game_factory([player, other_player], last_raise_increment=raise_increment)
        action = Action(action_type=ActionType.CALL)

        updated_game = ActionApplier.apply_action(game, player, action)

        assert updated_game.betting_state.last_raise_increment == raise_increment


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
        game = minimal_game_factory([player, other_player], last_raise_increment=BIG_BLIND_STANDARD)
        action = Action(action_type=ActionType.RAISE, amount=raise_increment)

        updated_game = ActionApplier.apply_action(game, player, action)

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
        game = minimal_game_factory([player, other_player], last_raise_increment=BIG_BLIND_STANDARD)
        action = Action(action_type=ActionType.RAISE, amount=raise_increment)

        updated_game = ActionApplier.apply_action(game, player, action)

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
        game = minimal_game_factory([player, other_player], last_raise_increment=BIG_BLIND_STANDARD)
        action = Action(action_type=ActionType.RAISE, amount=raise_increment)

        updated_game = ActionApplier.apply_action(game, player, action)

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
        game = minimal_game_factory([player, other_player], last_raise_increment=BIG_BLIND_STANDARD)
        action = Action(action_type=ActionType.RAISE, amount=raise_increment)

        updated_game = ActionApplier.apply_action(game, player, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert updated_other_player.betting_status == BettingRoundActionStatus.NEEDS_ACTION

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
            [player, acted_player, folded_player], last_raise_increment=BIG_BLIND_STANDARD
        )
        action = Action(action_type=ActionType.RAISE, amount=raise_increment)

        updated_game = ActionApplier.apply_action(game, player, action)

        updated_folded_player = updated_game.get_player_by_id(folded_player.id)
        assert updated_folded_player is not None
        assert updated_folded_player.betting_status == BettingRoundActionStatus.ACTED

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
        game = minimal_game_factory([player, other_player], last_raise_increment=BIG_BLIND_STANDARD)
        action = Action(action_type=ActionType.RAISE, amount=raise_increment)

        updated_game = ActionApplier.apply_action(game, player, action)

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
        game = minimal_game_factory([player, other_player], last_raise_increment=BIG_BLIND_STANDARD)
        action = Action(action_type=ActionType.RAISE, amount=raise_increment)

        updated_game = ActionApplier.apply_action(game, player, action)

        assert updated_game.betting_state.last_raise_increment == raise_increment

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
            [player_a, player_b, player_c], last_raise_increment=BIG_BLIND_STANDARD
        )

        raise_action = Action(action_type=ActionType.RAISE, amount=raise_increment)
        game_after_raise = ActionApplier.apply_action(game, player_a, raise_action)
        assert game_after_raise.betting_state.last_raise_increment == raise_increment

        updated_player_b = game_after_raise.get_player_by_id(player_b.id)
        assert updated_player_b is not None
        assert updated_player_b.betting_status == BettingRoundActionStatus.NEEDS_ACTION

        updated_player_c = game_after_raise.get_player_by_id(player_c.id)
        assert updated_player_c is not None
        assert updated_player_c.betting_status == BettingRoundActionStatus.NEEDS_ACTION

        call_action = Action(action_type=ActionType.CALL)
        game_after_call_b = ActionApplier.apply_action(
            game_after_raise, updated_player_b, call_action
        )
        assert game_after_call_b.betting_state.last_raise_increment == raise_increment

        game_after_call_c = ActionApplier.apply_action(
            game_after_call_b, updated_player_c, call_action
        )
        assert game_after_call_c.betting_state.last_raise_increment == raise_increment

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
            [player, acted_player_1, acted_player_2], last_raise_increment=BIG_BLIND_STANDARD
        )
        action = Action(action_type=ActionType.RAISE, amount=raise_increment)

        updated_game = ActionApplier.apply_action(game, player, action)

        updated_acted_player_1 = updated_game.get_player_by_id(acted_player_1.id)
        assert updated_acted_player_1 is not None
        assert updated_acted_player_1.betting_status == BettingRoundActionStatus.NEEDS_ACTION

        updated_acted_player_2 = updated_game.get_player_by_id(acted_player_2.id)
        assert updated_acted_player_2 is not None
        assert updated_acted_player_2.betting_status == BettingRoundActionStatus.NEEDS_ACTION


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

        updated_game = ActionApplier.apply_action(game, player, action)

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

        updated_game = ActionApplier.apply_action(game, player, action)

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

        updated_game = ActionApplier.apply_action(game, player, action)

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

        updated_game = ActionApplier.apply_action(game, player, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert updated_other_player.betting_status == BettingRoundActionStatus.ACTED

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

        updated_game = ActionApplier.apply_action(game, player, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert updated_other_player.betting_status == BettingRoundActionStatus.NEEDS_ACTION
        assert updated_game.betting_state.last_raise_increment == expected_raise_increment

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

        updated_game = ActionApplier.apply_action(game, player, action)

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

        updated_game = ActionApplier.apply_action(game, player, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert updated_other_player.betting_status == BettingRoundActionStatus.ACTED
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
            [player, other_player], last_raise_increment=minimum_raise_increment
        )
        action = Action(action_type=ActionType.ALL_IN, amount=all_in_amount)

        updated_game = ActionApplier.apply_action(game, player, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert updated_other_player.betting_status == BettingRoundActionStatus.ACTED
        assert updated_game.betting_state.last_raise_increment == minimum_raise_increment

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
            [player, other_player], last_raise_increment=minimum_raise_increment
        )
        action = Action(action_type=ActionType.ALL_IN, amount=all_in_amount)

        updated_game = ActionApplier.apply_action(game, player, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert updated_other_player.betting_status == BettingRoundActionStatus.NEEDS_ACTION
        assert updated_game.betting_state.last_raise_increment == raise_increment

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
            [player, other_player], last_raise_increment=minimum_raise_increment
        )
        action = Action(action_type=ActionType.ALL_IN, amount=all_in_amount)

        updated_game = ActionApplier.apply_action(game, player, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert updated_other_player.betting_status == BettingRoundActionStatus.NEEDS_ACTION
        assert updated_game.betting_state.last_raise_increment == raise_increment

    def test_all_in_when_no_call_amount_and_all_in_less_than_big_blind_treated_as_call_does_not_reopen(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        all_in_amount = ChipAmount(10)
        assert all_in_amount.value < BIG_BLIND_STANDARD.value
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

        updated_game = ActionApplier.apply_action(game, player, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert updated_other_player.betting_status == BettingRoundActionStatus.ACTED
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

        updated_game = ActionApplier.apply_action(game, player, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert updated_other_player.betting_status == BettingRoundActionStatus.NEEDS_ACTION
        assert updated_game.betting_state.last_raise_increment == all_in_amount


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
        game.hand_state.current_phase = GamePhase.FLOP
        action = Action(action_type=ActionType.BET, amount=bet_amount)

        updated_game = ActionApplier.apply_action(game, player, action)

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
        game.hand_state.current_phase = GamePhase.FLOP
        action = Action(action_type=ActionType.BET, amount=bet_amount)

        updated_game = ActionApplier.apply_action(game, player, action)

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
        game.hand_state.current_phase = GamePhase.FLOP
        action = Action(action_type=ActionType.BET, amount=bet_amount)

        updated_game = ActionApplier.apply_action(game, player, action)

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
        game.hand_state.current_phase = GamePhase.FLOP
        action = Action(action_type=ActionType.BET, amount=bet_amount)

        updated_game = ActionApplier.apply_action(game, player, action)

        updated_other_player = updated_game.get_player_by_id(other_player.id)
        assert updated_other_player is not None
        assert updated_other_player.betting_status == BettingRoundActionStatus.NEEDS_ACTION

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
        game.hand_state.current_phase = GamePhase.FLOP
        action = Action(action_type=ActionType.BET, amount=bet_amount)

        updated_game = ActionApplier.apply_action(game, player, action)

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
        game.hand_state.current_phase = GamePhase.FLOP
        action = Action(action_type=ActionType.BET, amount=bet_amount)

        updated_game = ActionApplier.apply_action(game, player, action)

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
        game.hand_state.current_phase = GamePhase.FLOP
        action = Action(action_type=ActionType.BET, amount=bet_amount)

        updated_game = ActionApplier.apply_action(game, player, action)

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
        game.hand_state.current_phase = GamePhase.FLOP
        action = Action(action_type=ActionType.BET, amount=bet_amount)

        updated_game = ActionApplier.apply_action(game, player, action)

        updated_folded_player = updated_game.get_player_by_id(folded_player.id)
        assert updated_folded_player is not None
        assert updated_folded_player.betting_status == BettingRoundActionStatus.ACTED

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
        game.hand_state.current_phase = GamePhase.FLOP
        action = Action(action_type=ActionType.BET, amount=bet_amount)

        updated_game = ActionApplier.apply_action(game, player, action)

        updated_acted_player_1 = updated_game.get_player_by_id(acted_player_1.id)
        assert updated_acted_player_1 is not None
        assert updated_acted_player_1.betting_status == BettingRoundActionStatus.NEEDS_ACTION

        updated_acted_player_2 = updated_game.get_player_by_id(acted_player_2.id)
        assert updated_acted_player_2 is not None
        assert updated_acted_player_2.betting_status == BettingRoundActionStatus.NEEDS_ACTION

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

        for phase in [GamePhase.FLOP, GamePhase.TURN, GamePhase.RIVER]:
            game = minimal_game_factory([player, other_player])
            game.hand_state.current_phase = phase
            action = Action(action_type=ActionType.BET, amount=bet_amount)

            updated_game = ActionApplier.apply_action(game, player, action)

            updated_player = updated_game.get_player_by_id(player.id)
            assert updated_player is not None
            assert updated_player.remaining_chips == ChipAmount(150)
            assert updated_game.betting_state.last_raise_increment == bet_amount


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
        game.hand_state.current_phase = GamePhase.FLOP
        bet_amount = ChipAmount(10)
        assert bet_amount.value < BIG_BLIND_STANDARD.value
        action = Action(action_type=ActionType.BET, amount=bet_amount)

        with pytest.raises(ValueError, match="Bet amount .* is below minimum"):
            ActionApplier.apply_action(game, player, action)

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
        game.hand_state.current_phase = GamePhase.FLOP
        bet_amount = ChipAmount(100)
        assert bet_amount.value > player.remaining_chips.value
        action = Action(action_type=ActionType.BET, amount=bet_amount)

        with pytest.raises(ValueError, match="Bet amount .* exceeds maximum"):
            ActionApplier.apply_action(game, player, action)

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

        with pytest.raises(ValueError, match="All-in amount .* does not match"):
            ActionApplier.apply_action(game, player, action)

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
        game.hand_state.current_phase = GamePhase.FLOP
        action = Action(action_type=ActionType.RAISE, amount=ChipAmount(50))

        with pytest.raises(ValueError, match="Action raise is not available"):
            ActionApplier.apply_action(game, player, action)


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
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=MEDIUM_CHIPS,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        player3 = sample_player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=MEDIUM_CHIPS,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player1, player2, player3])
        game.betting_state.current_player_position = 0
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player1, action)

        assert updated_game.betting_state.current_player_position == 1

    def test_wraps_around_to_first_player_when_last_player_acts(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=MEDIUM_CHIPS,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        game = minimal_game_factory([player1, player2])
        game.betting_state.current_player_position = 1
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player2, action)

        assert updated_game.betting_state.current_player_position == NO_CURRENT_PLAYER

    def test_returns_none_when_no_players_need_action(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        player2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=MEDIUM_CHIPS,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player1, player2])
        game.betting_state.current_player_position = 0
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player1, action)

        assert updated_game.betting_state.current_player_position == NO_CURRENT_PLAYER

    def test_skips_folded_players_when_finding_next_player(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        folded_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=MEDIUM_CHIPS,
            participation_status=HandParticipationStatus.FOLDED,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        player3 = sample_player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=MEDIUM_CHIPS,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        game = minimal_game_factory([player1, folded_player, player3])
        game.betting_state.current_player_position = 0
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player1, action)

        assert updated_game.betting_state.current_player_position == 2

    def test_skips_players_who_have_already_acted_when_finding_next_player(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player1 = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=MEDIUM_CHIPS,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        acted_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=MEDIUM_CHIPS,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        player3 = sample_player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=MEDIUM_CHIPS,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        game = minimal_game_factory([player1, acted_player, player3])
        game.betting_state.current_player_position = 0
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player1, action)

        assert updated_game.betting_state.current_player_position == 2

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
        game = minimal_game_factory([player1, player2], last_raise_increment=BIG_BLIND_STANDARD)
        game.betting_state.current_player_position = 0
        action = Action(action_type=ActionType.RAISE, amount=ChipAmount(50))

        updated_game = ActionApplier.apply_action(game, player1, action)

        assert updated_game.betting_state.current_player_position == 1


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
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        original_player_chips = player.remaining_chips
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player, action)

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
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player, action)

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
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player, action)

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
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player, action)

        assert updated_game.hand_state == game.hand_state

    def test_preserves_pot_state_after_action(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
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
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player, action)

        assert updated_game.pot_state == game.pot_state

    def test_preserves_button_seat_after_action(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
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
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player, action)

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
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player, action)

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
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.CHECK)

        updated_game = ActionApplier.apply_action(game, player, action)

        assert updated_game.results == game.results


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_fold_when_player_has_hole_cards_clears_them(
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
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        player.hole_cards = hole_cards
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=LARGE_CHIPS,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        action = Action(action_type=ActionType.FOLD)

        updated_game = ActionApplier.apply_action(game, player, action)

        updated_player = updated_game.get_player_by_id(player.id)
        assert updated_player is not None
        assert updated_player.hole_cards is None

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

        updated_game = ActionApplier.apply_action(game, player, action)

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
        game = minimal_game_factory([player, other_player], last_raise_increment=BIG_BLIND_STANDARD)
        action = Action(action_type=ActionType.RAISE, amount=minimum_raise)

        updated_game = ActionApplier.apply_action(game, player, action)

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
        game = minimal_game_factory([player, other_player], last_raise_increment=BIG_BLIND_STANDARD)
        action = Action(action_type=ActionType.RAISE, amount=max_raise)

        updated_game = ActionApplier.apply_action(game, player, action)

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

        updated_game = ActionApplier.apply_action(game, player, action)

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

        updated_game = ActionApplier.apply_action(game, player, action)

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
            [player, acted_player, eliminated_player], last_raise_increment=BIG_BLIND_STANDARD
        )
        action = Action(action_type=ActionType.RAISE, amount=raise_increment)

        updated_game = ActionApplier.apply_action(game, player, action)

        updated_eliminated_player = updated_game.get_player_by_id(eliminated_player.id)
        assert updated_eliminated_player is not None
        assert updated_eliminated_player.betting_status == BettingRoundActionStatus.ACTED
