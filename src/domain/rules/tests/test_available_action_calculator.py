"""Tests for AvailableActionCalculator - calculates available actions for players."""

from __future__ import annotations

from collections.abc import Callable

from src.domain.models.available_action import (
    AvailableAllInAction,
    AvailableBetAction,
    AvailableCallAction,
    AvailableCheckAction,
    AvailableFoldAction,
    AvailableRaiseAction,
)
from src.domain.models.chips import ChipAmount
from src.domain.models.game import Game, HandPhase
from src.domain.models.player import (
    BettingRoundActionStatus,
    HandParticipationStatus,
    Player,
)
from src.domain.models.seat import Seat
from src.domain.rules.available_action_calculator import (
    AvailableActionCalculator,
)


class TestPlayerCannotAct:
    """Tests when player cannot act - should return empty list."""

    def test_returns_empty_list_when_player_has_no_chips(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        dummy_player = sample_player_factory(
            player_id="dummy-player",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            participation_status=HandParticipationStatus.FOLDED,
        )
        game = minimal_game_factory([player, dummy_player])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        assert result == []

    def test_returns_empty_list_when_player_has_already_acted(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(100),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        dummy_player = sample_player_factory(
            player_id="dummy-player",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            participation_status=HandParticipationStatus.FOLDED,
        )
        game = minimal_game_factory([player, dummy_player])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        assert result == []

    def test_returns_empty_list_when_player_has_no_chips_and_already_acted(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(0),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        dummy_player = sample_player_factory(
            player_id="dummy-player",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            participation_status=HandParticipationStatus.FOLDED,
        )
        game = minimal_game_factory([player, dummy_player])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        assert result == []


class TestFoldAction:
    """Tests for FOLD action availability."""

    def test_fold_always_available_when_player_can_act(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(100),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        dummy_player = sample_player_factory(
            player_id="dummy-player",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, dummy_player])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        fold_actions = [
            a for a in result if isinstance(a, AvailableFoldAction)
        ]
        assert len(fold_actions) == 1

    def test_fold_available_even_when_player_has_minimal_chips(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(1),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        dummy_player = sample_player_factory(
            player_id="dummy-player",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, dummy_player])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        fold_actions = [
            a for a in result if isinstance(a, AvailableFoldAction)
        ]
        assert len(fold_actions) == 1


class TestCheckAction:
    """Tests for CHECK action availability."""

    def test_check_available_when_call_amount_is_zero(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        dummy_player = sample_player_factory(
            player_id="dummy-player",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, dummy_player])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        check_actions = [
            a for a in result if isinstance(a, AvailableCheckAction)
        ]
        assert len(check_actions) == 1

    def test_check_available_when_player_already_matched_bet(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        dummy_player = sample_player_factory(
            player_id="dummy-player",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, dummy_player])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        check_actions = [
            a for a in result if isinstance(a, AvailableCheckAction)
        ]
        assert len(check_actions) == 1

    def test_check_not_available_when_call_amount_greater_than_zero(
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
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
        )
        game = minimal_game_factory([player, other_player])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        check_actions = [
            a for a in result if isinstance(a, AvailableCheckAction)
        ]
        assert len(check_actions) == 0


class TestCallAction:
    """Tests for CALL action availability."""

    def test_call_available_when_player_has_sufficient_chips_for_call(
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
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
        )
        game = minimal_game_factory([player, other_player])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        call_actions = [
            a for a in result if isinstance(a, AvailableCallAction)
        ]
        assert len(call_actions) == 1
        assert call_actions[0].call_amount == ChipAmount(30)

    def test_call_not_available_when_call_amount_is_zero(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        dummy_player = sample_player_factory(
            player_id="dummy-player",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            participation_status=HandParticipationStatus.FOLDED,
        )
        game = minimal_game_factory([player, dummy_player])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        call_actions = [
            a for a in result if isinstance(a, AvailableCallAction)
        ]
        assert len(call_actions) == 0

    def test_call_not_available_when_player_has_insufficient_chips(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(20),
            total_invested_this_hand=ChipAmount(10),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
        )
        game = minimal_game_factory([player, other_player])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        call_actions = [
            a for a in result if isinstance(a, AvailableCallAction)
        ]
        assert len(call_actions) == 0

    def test_call_available_when_player_has_exactly_enough_chips(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(30),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
        )
        game = minimal_game_factory([player, other_player])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        call_actions = [
            a for a in result if isinstance(a, AvailableCallAction)
        ]
        assert len(call_actions) == 1
        assert call_actions[0].call_amount == ChipAmount(30)


class TestRaiseAction:
    """Tests for RAISE action availability."""

    def test_raise_available_when_player_has_chips_beyond_call_and_meets_minimum_increment(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
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
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
        )
        game = minimal_game_factory(
            [player, other_player],
            last_raise_increment=ChipAmount(0),
        )

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        raise_actions = [
            a for a in result if isinstance(a, AvailableRaiseAction)
        ]
        assert len(raise_actions) == 1
        assert raise_actions[0].min_raise_amount == ChipAmount(20)
        assert raise_actions[0].max_raise_amount == ChipAmount(170)

    def test_raise_min_amount_uses_big_blind_when_first_raise(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
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
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
        )
        game = minimal_game_factory(
            [player, other_player],
            last_raise_increment=ChipAmount(0),
        )

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        raise_actions = [
            a for a in result if isinstance(a, AvailableRaiseAction)
        ]
        assert raise_actions[0].min_raise_amount == ChipAmount(20)

    def test_raise_min_amount_uses_last_raise_increment_when_re_raising(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
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
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
        )
        game = minimal_game_factory(
            [player, other_player],
            last_raise_increment=ChipAmount(40),
        )

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        raise_actions = [
            a for a in result if isinstance(a, AvailableRaiseAction)
        ]
        assert raise_actions[0].min_raise_amount == ChipAmount(40)

    def test_raise_max_amount_is_chips_available_after_call(
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
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
        )
        game = minimal_game_factory(
            [player, other_player],
            last_raise_increment=ChipAmount(0),
        )

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        raise_actions = [
            a for a in result if isinstance(a, AvailableRaiseAction)
        ]
        assert raise_actions[0].max_raise_amount == ChipAmount(70)

    def test_raise_not_available_when_player_has_insufficient_chips_for_minimum_raise(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(35),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
        )
        game = minimal_game_factory(
            [player, other_player],
            last_raise_increment=ChipAmount(0),
        )

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        raise_actions = [
            a for a in result if isinstance(a, AvailableRaiseAction)
        ]
        assert len(raise_actions) == 0

    def test_raise_not_available_when_chips_after_call_less_than_minimum_increment(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(50),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
        )
        game = minimal_game_factory(
            [player, other_player],
            last_raise_increment=ChipAmount(30),
        )

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        raise_actions = [
            a for a in result if isinstance(a, AvailableRaiseAction)
        ]
        assert len(raise_actions) == 0

    def test_raise_not_available_when_player_has_no_chips_beyond_call(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(30),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
        )
        game = minimal_game_factory(
            [player, other_player],
            last_raise_increment=ChipAmount(0),
        )

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        raise_actions = [
            a for a in result if isinstance(a, AvailableRaiseAction)
        ]
        assert len(raise_actions) == 0


class TestAllInAction:
    """Tests for ALL_IN action availability."""

    def test_all_in_available_when_player_has_chips(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(100),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        dummy_player = sample_player_factory(
            player_id="dummy-player",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, dummy_player])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        all_in_actions = [
            a for a in result if isinstance(a, AvailableAllInAction)
        ]
        assert len(all_in_actions) == 1
        assert all_in_actions[0].all_in_amount == ChipAmount(100)

    def test_all_in_amount_matches_player_chips(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(75),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        dummy_player = sample_player_factory(
            player_id="dummy-player",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, dummy_player])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        all_in_actions = [
            a for a in result if isinstance(a, AvailableAllInAction)
        ]
        assert all_in_actions[0].all_in_amount == ChipAmount(75)

    def test_all_in_not_available_when_player_has_zero_chips(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        dummy_player = sample_player_factory(
            player_id="dummy-player",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            participation_status=HandParticipationStatus.FOLDED,
        )
        game = minimal_game_factory([player, dummy_player])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        all_in_actions = [
            a for a in result if isinstance(a, AvailableAllInAction)
        ]
        assert len(all_in_actions) == 0


class TestActionCombinations:
    """Tests for scenarios where multiple actions are available simultaneously."""

    def test_fold_and_check_available_when_call_amount_is_zero(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        dummy_player = sample_player_factory(
            player_id="dummy-player",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, dummy_player])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        action_types = {type(a) for a in result}
        assert AvailableFoldAction in action_types
        assert AvailableCheckAction in action_types
        assert AvailableAllInAction in action_types
        assert AvailableRaiseAction in action_types

    def test_fold_and_call_available_when_call_amount_greater_than_zero(
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
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
        )
        game = minimal_game_factory([player, other_player])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        action_types = {type(a) for a in result}
        assert AvailableFoldAction in action_types
        assert AvailableCallAction in action_types
        assert AvailableAllInAction in action_types
        assert AvailableCheckAction not in action_types

    def test_fold_call_raise_and_all_in_available_when_player_has_sufficient_chips(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
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
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
        )
        game = minimal_game_factory(
            [player, other_player],
            last_raise_increment=ChipAmount(0),
        )

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        action_types = {type(a) for a in result}
        assert AvailableFoldAction in action_types
        assert AvailableCallAction in action_types
        assert AvailableRaiseAction in action_types
        assert AvailableAllInAction in action_types
        assert AvailableCheckAction not in action_types

    def test_fold_and_all_in_only_when_player_cannot_call_or_raise(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(10),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
        )
        game = minimal_game_factory([player, other_player])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        action_types = {type(a) for a in result}
        assert AvailableFoldAction in action_types
        assert AvailableAllInAction in action_types
        assert AvailableCallAction not in action_types
        assert AvailableRaiseAction not in action_types
        assert AvailableCheckAction not in action_types


class TestNoOpponentsRemaining:
    """Tests when all other players have folded or are eliminated."""

    def test_returns_empty_list_when_all_other_players_folded(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        active_player = sample_player_factory(
            player_id="active-player",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(100),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        folded_player1 = sample_player_factory(
            player_id="folded-1",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(500),
            participation_status=HandParticipationStatus.FOLDED,
        )
        folded_player2 = sample_player_factory(
            player_id="folded-2",
            seat=Seat.SEAT_2,
            remaining_chips=ChipAmount(500),
            participation_status=HandParticipationStatus.FOLDED,
        )
        game = minimal_game_factory(
            [active_player, folded_player1, folded_player2]
        )

        result = AvailableActionCalculator.calculate_available_actions(
            game, active_player.id
        )

        assert result == []

    def test_returns_empty_list_when_all_other_players_eliminated(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        active_player = sample_player_factory(
            player_id="active-player",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(100),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        eliminated_player = sample_player_factory(
            player_id="eliminated-1",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(0),
            participation_status=HandParticipationStatus.ELIMINATED,
        )
        game = minimal_game_factory([active_player, eliminated_player])

        result = AvailableActionCalculator.calculate_available_actions(
            game, active_player.id
        )

        assert result == []

    def test_returns_empty_list_when_mix_of_folded_and_eliminated(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        active_player = sample_player_factory(
            player_id="active-player",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(100),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        folded_player = sample_player_factory(
            player_id="folded-1",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(500),
            participation_status=HandParticipationStatus.FOLDED,
        )
        eliminated_player = sample_player_factory(
            player_id="eliminated-1",
            seat=Seat.SEAT_2,
            remaining_chips=ChipAmount(0),
            participation_status=HandParticipationStatus.ELIMINATED,
        )
        game = minimal_game_factory(
            [active_player, folded_player, eliminated_player]
        )

        result = AvailableActionCalculator.calculate_available_actions(
            game, active_player.id
        )

        assert result == []


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_player_with_minimal_chips_facing_no_bet_gets_fold_check_all_in(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(1),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        opponent = sample_player_factory(
            player_id="opponent",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(0),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, opponent])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        action_types = {type(a) for a in result}
        assert AvailableFoldAction in action_types
        assert AvailableCheckAction in action_types
        assert AvailableAllInAction in action_types
        assert AvailableCallAction not in action_types
        assert AvailableRaiseAction not in action_types

    def test_player_with_minimal_chips_facing_bet_gets_fold_and_all_in_only(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(5),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        opponent = sample_player_factory(
            player_id="opponent",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(100),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, opponent])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        action_types = {type(a) for a in result}
        assert AvailableFoldAction in action_types
        assert AvailableAllInAction in action_types
        assert AvailableCallAction not in action_types
        assert AvailableRaiseAction not in action_types
        assert AvailableCheckAction not in action_types

    def test_player_already_all_in_returns_empty_list(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(100),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
        )
        game = minimal_game_factory([player, other_player])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        assert result == []

    def test_player_folded_returns_empty_list(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(100),
            participation_status=HandParticipationStatus.FOLDED,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        dummy_player = sample_player_factory(
            player_id="dummy-player",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            participation_status=HandParticipationStatus.FOLDED,
        )
        game = minimal_game_factory([player, dummy_player])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        assert result == []

    def test_player_eliminated_returns_empty_list(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(100),
            participation_status=HandParticipationStatus.ELIMINATED,
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        dummy_player = sample_player_factory(
            player_id="dummy-player",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            participation_status=HandParticipationStatus.FOLDED,
        )
        game = minimal_game_factory([player, dummy_player])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        assert result == []

    def test_raise_min_amount_uses_big_blind_when_last_increment_smaller(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
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
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
        )
        game = minimal_game_factory(
            [player, other_player],
            last_raise_increment=ChipAmount(10),
        )

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        raise_actions = [
            a for a in result if isinstance(a, AvailableRaiseAction)
        ]
        assert raise_actions[0].min_raise_amount == ChipAmount(20)

    def test_call_amount_correctly_calculated_when_other_players_have_higher_bets(
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
        other_player1 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(100),
        )
        other_player2 = sample_player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
        )
        game = minimal_game_factory([player, other_player1, other_player2])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        call_actions = [
            a for a in result if isinstance(a, AvailableCallAction)
        ]
        assert call_actions[0].call_amount == ChipAmount(80)

    def test_raise_available_when_min_equals_max(
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
        opponent = sample_player_factory(
            player_id="opponent",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(10),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, opponent],
            last_raise_increment=ChipAmount(40),
        )

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        raise_actions = [
            a for a in result if isinstance(a, AvailableRaiseAction)
        ]
        assert len(raise_actions) == 1
        assert raise_actions[0].min_raise_amount == ChipAmount(40)
        assert raise_actions[0].max_raise_amount == ChipAmount(40)

    def test_actions_available_when_opponent_is_all_in(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(500),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        all_in_opponent = sample_player_factory(
            player_id="all-in-opponent",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(100),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, all_in_opponent],
            last_raise_increment=ChipAmount(0),
        )

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        action_types = {type(a) for a in result}
        assert AvailableFoldAction in action_types
        assert AvailableCallAction in action_types
        assert AvailableRaiseAction in action_types
        assert AvailableAllInAction in action_types

        call_actions = [
            a for a in result if isinstance(a, AvailableCallAction)
        ]
        assert call_actions[0].call_amount == ChipAmount(80)

    def test_big_blind_option_check_available_when_facing_limp(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        big_blind_player = sample_player_factory(
            player_id="big-blind",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(980),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        limping_player = sample_player_factory(
            player_id="limper",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(980),
            total_invested_this_hand=ChipAmount(20),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [big_blind_player, limping_player],
            last_raise_increment=ChipAmount(0),
        )

        result = AvailableActionCalculator.calculate_available_actions(
            game, big_blind_player.id
        )

        action_types = {type(a) for a in result}
        assert AvailableFoldAction in action_types
        assert AvailableCheckAction in action_types
        assert AvailableRaiseAction in action_types
        assert AvailableAllInAction in action_types
        assert AvailableCallAction not in action_types

    def test_multiway_pot_with_different_bet_levels(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(500),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        raiser = sample_player_factory(
            player_id="raiser",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(800),
            total_invested_this_hand=ChipAmount(200),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        caller = sample_player_factory(
            player_id="caller",
            seat=Seat.SEAT_2,
            remaining_chips=ChipAmount(800),
            total_invested_this_hand=ChipAmount(200),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, raiser, caller],
            last_raise_increment=ChipAmount(180),
        )

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        call_actions = [
            a for a in result if isinstance(a, AvailableCallAction)
        ]
        raise_actions = [
            a for a in result if isinstance(a, AvailableRaiseAction)
        ]

        assert call_actions[0].call_amount == ChipAmount(180)
        assert raise_actions[0].min_raise_amount == ChipAmount(180)
        assert raise_actions[0].max_raise_amount == ChipAmount(320)

    def test_heads_up_facing_all_in_for_less(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(1000),
            total_invested_this_hand=ChipAmount(100),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        short_stack_all_in = sample_player_factory(
            player_id="short-stack",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(50),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, short_stack_all_in],
            last_raise_increment=ChipAmount(0),
        )

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        action_types = {type(a) for a in result}
        assert AvailableFoldAction in action_types
        assert AvailableCheckAction in action_types
        assert AvailableRaiseAction in action_types
        assert AvailableAllInAction in action_types
        assert AvailableCallAction not in action_types


class TestRaiseActionRules:
    """Tests for RAISE action availability rules across game phases."""

    def test_raise_available_preflop_when_call_amount_is_zero(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        big_blind_player = sample_player_factory(
            player_id="big-blind",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(980),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        limping_player = sample_player_factory(
            player_id="limper",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(980),
            total_invested_this_hand=ChipAmount(20),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [big_blind_player, limping_player],
            last_raise_increment=ChipAmount(0),
        )
        assert game.current_phase == HandPhase.PRE_FLOP

        result = AvailableActionCalculator.calculate_available_actions(
            game, big_blind_player.id
        )

        action_types = {type(a) for a in result}
        assert AvailableRaiseAction in action_types
        assert AvailableCheckAction in action_types
        assert AvailableFoldAction in action_types
        assert AvailableAllInAction in action_types
        assert AvailableBetAction not in action_types
        assert AvailableCallAction not in action_types

    def test_raise_available_preflop_when_call_amount_greater_than_zero(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        raiser = sample_player_factory(
            player_id="raiser",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory(
            [player, raiser],
            last_raise_increment=ChipAmount(0),
        )
        assert game.current_phase == HandPhase.PRE_FLOP

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        action_types = {type(a) for a in result}
        assert AvailableRaiseAction in action_types
        assert AvailableCallAction in action_types
        assert AvailableFoldAction in action_types
        assert AvailableBetAction not in action_types

    def test_raise_available_postflop_when_call_amount_greater_than_zero(
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
        better = sample_player_factory(
            player_id="better",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, better])
        game.hand_state.current_phase = HandPhase.FLOP

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        action_types = {type(a) for a in result}
        assert AvailableRaiseAction in action_types
        assert AvailableCallAction in action_types
        assert AvailableBetAction not in action_types

    def test_raise_not_available_postflop_when_call_amount_is_zero(
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
        checked_player = sample_player_factory(
            player_id="checked",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(0),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, checked_player])
        game.hand_state.current_phase = HandPhase.FLOP

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        action_types = {type(a) for a in result}
        assert AvailableRaiseAction not in action_types
        assert AvailableBetAction in action_types


class TestBetActionRules:
    """Tests for BET action availability rules across game phases."""

    def test_bet_not_available_preflop(
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
        checked_player = sample_player_factory(
            player_id="checked",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(0),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, checked_player])
        assert game.current_phase == HandPhase.PRE_FLOP

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        action_types = {type(a) for a in result}
        assert AvailableBetAction not in action_types
        assert AvailableRaiseAction in action_types
        assert AvailableFoldAction in action_types

    def test_bet_available_postflop_when_call_amount_is_zero_first_to_act(
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
        checked_player = sample_player_factory(
            player_id="checked",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(0),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, checked_player])
        game.hand_state.current_phase = HandPhase.FLOP

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        action_types = {type(a) for a in result}
        assert AvailableBetAction in action_types
        assert AvailableRaiseAction not in action_types
        bet_actions = [a for a in result if isinstance(a, AvailableBetAction)]
        assert len(bet_actions) == 1
        assert (
            bet_actions[0].min_bet_amount == game.current_blind_level.big_blind
        )
        assert bet_actions[0].max_bet_amount == player.remaining_chips

    def test_bet_available_postflop_on_turn_when_call_amount_is_zero(
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
        checked_player = sample_player_factory(
            player_id="checked",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(0),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, checked_player])
        game.hand_state.current_phase = HandPhase.TURN

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        action_types = {type(a) for a in result}
        assert AvailableBetAction in action_types
        assert AvailableRaiseAction not in action_types

    def test_bet_available_postflop_on_river_when_call_amount_is_zero(
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
        checked_player = sample_player_factory(
            player_id="checked",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(0),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, checked_player])
        game.hand_state.current_phase = HandPhase.RIVER

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        action_types = {type(a) for a in result}
        assert AvailableBetAction in action_types
        assert AvailableFoldAction in action_types
        assert AvailableRaiseAction not in action_types

    def test_bet_not_available_postflop_when_call_amount_greater_than_zero(
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
        better = sample_player_factory(
            player_id="better",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, better])
        game.hand_state.current_phase = HandPhase.FLOP

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        action_types = {type(a) for a in result}
        assert AvailableBetAction not in action_types
        assert AvailableRaiseAction in action_types
        assert AvailableCallAction in action_types
        assert AvailableFoldAction in action_types


class TestInputValidation:
    """Tests for input validation and error handling."""

    def test_raises_error_when_player_not_found(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Should raise ValueError when player ID not in game."""
        import pytest

        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(100),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other])

        with pytest.raises(ValueError, match="not found"):
            AvailableActionCalculator.calculate_available_actions(
                game, "non-existent-id"
            )


class TestMultiPlayerActionAvailability:
    """Tests for action availability in 3+ player scenarios."""

    def test_three_player_different_investments(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """In 3-player scenario with varying investments, call amount is max - player's investment."""
        # Player 1: invested 20, Player 2: invested 50, Player 3: invested 100
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        p2 = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(150),
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        p3 = sample_player_factory(
            player_id="player-3",
            seat=Seat.SEAT_2,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(100),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, p2, p3])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        # Player 1 needs to call 80 (100 - 20)
        call_action = next(
            a for a in result if isinstance(a, AvailableCallAction)
        )
        assert call_action.call_amount == ChipAmount(80)

    def test_four_player_one_folded_one_all_in(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """4-player scenario: one folded, one all-in, two active."""
        player = sample_player_factory(
            player_id="player",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        all_in = sample_player_factory(
            player_id="all-in",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        folded = sample_player_factory(
            player_id="folded",
            seat=Seat.SEAT_2,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(20),
            participation_status=HandParticipationStatus.FOLDED,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        active = sample_player_factory(
            player_id="active",
            seat=Seat.SEAT_3,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, all_in, folded, active])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        # Player should have fold, call, raise, all-in available
        action_types = {type(a) for a in result}
        assert AvailableFoldAction in action_types
        assert AvailableCallAction in action_types
        assert AvailableAllInAction in action_types

    def test_five_player_scenario(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """5-player scenario with complex state."""
        players = [
            sample_player_factory(
                player_id=f"p{i}",
                seat=Seat(i),
                remaining_chips=ChipAmount(100 + i * 50),
                total_invested_this_hand=ChipAmount(50),
                betting_status=(
                    BettingRoundActionStatus.NEEDS_ACTION
                    if i == 0
                    else BettingRoundActionStatus.ACTED
                ),
            )
            for i in range(5)
        ]
        game = minimal_game_factory(players)

        result = AvailableActionCalculator.calculate_available_actions(
            game, players[0].id
        )

        # All players at 50, so check is available
        action_types = {type(a) for a in result}
        assert AvailableCheckAction in action_types
        assert AvailableFoldAction in action_types


class TestBetMinMaxBoundaries:
    """Tests for bet minimum and maximum amount boundaries."""

    def test_bet_min_equals_big_blind(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Minimum bet amount should equal big blind."""
        player = sample_player_factory(
            player_id="player",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other = sample_player_factory(
            player_id="other",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other])
        game.hand_state.current_phase = HandPhase.FLOP

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        bet_action = next(
            a for a in result if isinstance(a, AvailableBetAction)
        )
        # BB is 20 (from conftest.py)
        assert bet_action.min_bet_amount == ChipAmount(20)

    def test_bet_max_equals_remaining_chips(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Maximum bet amount should equal player's remaining chips."""
        remaining = ChipAmount(175)
        player = sample_player_factory(
            player_id="player",
            seat=Seat.SEAT_0,
            remaining_chips=remaining,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other = sample_player_factory(
            player_id="other",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other])
        game.hand_state.current_phase = HandPhase.FLOP

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        bet_action = next(
            a for a in result if isinstance(a, AvailableBetAction)
        )
        assert bet_action.max_bet_amount == remaining

    def test_bet_not_available_when_chips_less_than_minimum(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """BET not available when player has less chips than minimum bet."""
        player = sample_player_factory(
            player_id="player",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(15),  # Less than BB of 20
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other = sample_player_factory(
            player_id="other",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other])
        game.hand_state.current_phase = HandPhase.FLOP

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        action_types = {type(a) for a in result}
        assert AvailableBetAction not in action_types
        # But all-in should be available
        assert AvailableAllInAction in action_types


class TestRaiseMinMaxBoundaries:
    """Tests for raise minimum and maximum amount boundaries."""

    def test_raise_min_uses_big_blind_when_no_prior_raise(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Minimum raise should use BB when no prior raise."""
        player = sample_player_factory(
            player_id="player",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        bettor = sample_player_factory(
            player_id="bettor",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        # No last_raise_increment set (or 0)
        game = minimal_game_factory(
            [player, bettor], last_raise_increment=ChipAmount(0)
        )

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        raise_action = next(
            a for a in result if isinstance(a, AvailableRaiseAction)
        )
        # BB is 20, so min raise is 20
        assert raise_action.min_raise_amount == ChipAmount(20)

    def test_raise_min_uses_last_raise_when_greater_than_bb(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Minimum raise uses last raise size when greater than BB."""
        player = sample_player_factory(
            player_id="player",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(500),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        raiser = sample_player_factory(
            player_id="raiser",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(400),
            total_invested_this_hand=ChipAmount(100),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        # Last raise was 100
        game = minimal_game_factory(
            [player, raiser], last_raise_increment=ChipAmount(100)
        )

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        raise_action = next(
            a for a in result if isinstance(a, AvailableRaiseAction)
        )
        # min raise should be 100, not BB (20)
        assert raise_action.min_raise_amount == ChipAmount(100)

    def test_raise_max_is_chips_minus_call(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Maximum raise is remaining chips minus call amount."""
        player = sample_player_factory(
            player_id="player",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        bettor = sample_player_factory(
            player_id="bettor",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, bettor])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        raise_action = next(
            a for a in result if isinstance(a, AvailableRaiseAction)
        )
        # Call is 50, remaining is 200, so max raise is 150
        assert raise_action.max_raise_amount == ChipAmount(150)


class TestBigBlindOption:
    """Tests for big blind option scenario."""

    def test_bb_can_check_when_all_limped(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Big blind can check when everyone has just called (limped)."""
        bb = sample_player_factory(
            player_id="bb",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(20),  # Posted BB
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        limper = sample_player_factory(
            player_id="limper",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(180),
            total_invested_this_hand=ChipAmount(20),  # Called BB
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([bb, limper])

        result = AvailableActionCalculator.calculate_available_actions(
            game, bb.id
        )

        action_types = {type(a) for a in result}
        assert AvailableCheckAction in action_types

    def test_bb_can_raise_when_all_limped(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Big blind can raise when everyone has just called (limped)."""
        bb = sample_player_factory(
            player_id="bb",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        limper = sample_player_factory(
            player_id="limper",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(180),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([bb, limper])

        result = AvailableActionCalculator.calculate_available_actions(
            game, bb.id
        )

        action_types = {type(a) for a in result}
        assert AvailableRaiseAction in action_types

    def test_bb_cannot_check_when_facing_raise(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Big blind cannot check when someone has raised."""
        bb = sample_player_factory(
            player_id="bb",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        raiser = sample_player_factory(
            player_id="raiser",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(140),
            total_invested_this_hand=ChipAmount(60),  # Raised to 60
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([bb, raiser])

        result = AvailableActionCalculator.calculate_available_actions(
            game, bb.id
        )

        action_types = {type(a) for a in result}
        assert AvailableCheckAction not in action_types
        assert AvailableCallAction in action_types


class TestSmallBlindPreflop:
    """Tests for small blind preflop scenarios."""

    def test_sb_cannot_check_facing_bb(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Small blind cannot check when facing big blind."""
        sb = sample_player_factory(
            player_id="sb",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(10),  # Posted SB
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        bb = sample_player_factory(
            player_id="bb",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(180),
            total_invested_this_hand=ChipAmount(20),  # Posted BB
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([sb, bb])

        result = AvailableActionCalculator.calculate_available_actions(
            game, sb.id
        )

        action_types = {type(a) for a in result}
        assert AvailableCheckAction not in action_types
        assert AvailableCallAction in action_types

    def test_sb_call_amount_is_bb_minus_sb(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Small blind's call amount is BB - SB."""
        sb = sample_player_factory(
            player_id="sb",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(10),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        bb = sample_player_factory(
            player_id="bb",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(180),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([sb, bb])

        result = AvailableActionCalculator.calculate_available_actions(
            game, sb.id
        )

        call_action = next(
            a for a in result if isinstance(a, AvailableCallAction)
        )
        # Call amount is 20 - 10 = 10
        assert call_action.call_amount == ChipAmount(10)


class TestCanRaiseRestrictions:
    """Tests for can_raise flag restricting RAISE/BET availability (Rule 8.3 / WSOP Rule 96)."""

    def test_raise_not_available_when_can_raise_is_false_facing_bet(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """When can_raise=False (after short all-in), RAISE not available."""
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
            can_raise=False,  # Blocked by short all-in
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        action_types = {type(a) for a in result}
        assert AvailableRaiseAction not in action_types
        assert AvailableFoldAction in action_types
        assert AvailableCallAction in action_types
        assert AvailableAllInAction in action_types

    def test_bet_not_available_when_can_raise_is_false_postflop(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """When can_raise=False postflop with no bet facing, BET not available."""
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
            can_raise=False,  # Blocked by short all-in
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(0),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])
        game.hand_state.current_phase = HandPhase.FLOP

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        action_types = {type(a) for a in result}
        assert AvailableBetAction not in action_types
        assert AvailableFoldAction in action_types
        assert AvailableCheckAction in action_types
        assert AvailableAllInAction in action_types

    def test_raise_not_available_when_can_raise_is_false_preflop_bb_option(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """When can_raise=False preflop BB option, RAISE not available."""
        bb_player = sample_player_factory(
            player_id="big-blind",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(20),  # Posted BB
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
            can_raise=False,  # Blocked by short all-in
        )
        limper = sample_player_factory(
            player_id="limper",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(180),
            total_invested_this_hand=ChipAmount(20),  # Limped
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([bb_player, limper])
        assert game.current_phase == HandPhase.PRE_FLOP

        result = AvailableActionCalculator.calculate_available_actions(
            game, bb_player.id
        )

        action_types = {type(a) for a in result}
        assert AvailableRaiseAction not in action_types
        assert AvailableFoldAction in action_types
        assert AvailableCheckAction in action_types
        assert AvailableAllInAction in action_types

    def test_raise_available_when_can_raise_is_true_default(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """Default can_raise=True allows RAISE when facing bet."""
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
            can_raise=True,  # Default
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        action_types = {type(a) for a in result}
        assert AvailableRaiseAction in action_types

    def test_call_always_available_regardless_of_can_raise(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """CALL is always available when facing bet, even with can_raise=False."""
        player = sample_player_factory(
            player_id="player-1",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(200),
            total_invested_this_hand=ChipAmount(20),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
            can_raise=False,  # Blocked, but CALL should still work
        )
        other_player = sample_player_factory(
            player_id="player-2",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
            participation_status=HandParticipationStatus.IN_HAND,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other_player])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        call_actions = [
            a for a in result if isinstance(a, AvailableCallAction)
        ]
        assert len(call_actions) == 1
        assert call_actions[0].call_amount == ChipAmount(30)


class TestAllInAmountCorrectness:
    """Tests to verify all-in amount is always correct."""

    def test_all_in_amount_equals_remaining_chips(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """All-in amount should exactly equal remaining chips."""
        remaining = ChipAmount(73)  # Odd amount to verify exactness
        player = sample_player_factory(
            player_id="player",
            seat=Seat.SEAT_0,
            remaining_chips=remaining,
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other = sample_player_factory(
            player_id="other",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(0),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        all_in = next(a for a in result if isinstance(a, AvailableAllInAction))
        assert all_in.all_in_amount == remaining

    def test_all_in_not_available_with_zero_chips(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        """All-in not available when player has zero chips."""
        player = sample_player_factory(
            player_id="player",
            seat=Seat.SEAT_0,
            remaining_chips=ChipAmount(0),
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.NEEDS_ACTION,
        )
        other = sample_player_factory(
            player_id="other",
            seat=Seat.SEAT_1,
            remaining_chips=ChipAmount(100),
            total_invested_this_hand=ChipAmount(50),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        game = minimal_game_factory([player, other])

        result = AvailableActionCalculator.calculate_available_actions(
            game, player.id
        )

        action_types = {type(a) for a in result}
        assert AvailableAllInAction not in action_types
