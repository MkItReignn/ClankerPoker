"""Tests for AvailableActionCalculator - calculates available actions for players."""

from __future__ import annotations

from collections.abc import Callable

from src.domain.models.available_action import (AvailableAllInAction,
                                                AvailableBetAction,
                                                AvailableCallAction,
                                                AvailableCheckAction,
                                                AvailableFoldAction,
                                                AvailableRaiseAction)
from src.domain.models.chips import ChipAmount
from src.domain.models.game import Game, GamePhase
from src.domain.models.player import (BettingRoundActionStatus,
                                      HandParticipationStatus, Player)
from src.domain.models.seat import Seat
from src.domain.rules.available_action_calculator import \
    AvailableActionCalculator


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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

        fold_actions = [a for a in result if isinstance(a, AvailableFoldAction)]
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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

        fold_actions = [a for a in result if isinstance(a, AvailableFoldAction)]
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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

        check_actions = [a for a in result if isinstance(a, AvailableCheckAction)]
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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

        check_actions = [a for a in result if isinstance(a, AvailableCheckAction)]
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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

        check_actions = [a for a in result if isinstance(a, AvailableCheckAction)]
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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

        call_actions = [a for a in result if isinstance(a, AvailableCallAction)]
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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

        call_actions = [a for a in result if isinstance(a, AvailableCallAction)]
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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

        call_actions = [a for a in result if isinstance(a, AvailableCallAction)]
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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

        call_actions = [a for a in result if isinstance(a, AvailableCallAction)]
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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

        raise_actions = [a for a in result if isinstance(a, AvailableRaiseAction)]
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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

        raise_actions = [a for a in result if isinstance(a, AvailableRaiseAction)]
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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

        raise_actions = [a for a in result if isinstance(a, AvailableRaiseAction)]
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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

        raise_actions = [a for a in result if isinstance(a, AvailableRaiseAction)]
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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

        raise_actions = [a for a in result if isinstance(a, AvailableRaiseAction)]
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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

        raise_actions = [a for a in result if isinstance(a, AvailableRaiseAction)]
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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

        raise_actions = [a for a in result if isinstance(a, AvailableRaiseAction)]
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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

        all_in_actions = [a for a in result if isinstance(a, AvailableAllInAction)]
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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

        all_in_actions = [a for a in result if isinstance(a, AvailableAllInAction)]
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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

        all_in_actions = [a for a in result if isinstance(a, AvailableAllInAction)]
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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

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
        game = minimal_game_factory([active_player, folded_player1, folded_player2])

        result = AvailableActionCalculator.calculate_available_actions(game, active_player.id)

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

        result = AvailableActionCalculator.calculate_available_actions(game, active_player.id)

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
        game = minimal_game_factory([active_player, folded_player, eliminated_player])

        result = AvailableActionCalculator.calculate_available_actions(game, active_player.id)

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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

        raise_actions = [a for a in result if isinstance(a, AvailableRaiseAction)]
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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

        call_actions = [a for a in result if isinstance(a, AvailableCallAction)]
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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

        raise_actions = [a for a in result if isinstance(a, AvailableRaiseAction)]
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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

        action_types = {type(a) for a in result}
        assert AvailableFoldAction in action_types
        assert AvailableCallAction in action_types
        assert AvailableRaiseAction in action_types
        assert AvailableAllInAction in action_types

        call_actions = [a for a in result if isinstance(a, AvailableCallAction)]
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

        result = AvailableActionCalculator.calculate_available_actions(game, big_blind_player.id)

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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

        call_actions = [a for a in result if isinstance(a, AvailableCallAction)]
        raise_actions = [a for a in result if isinstance(a, AvailableRaiseAction)]

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

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

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
        assert game.current_phase == GamePhase.PRE_FLOP

        result = AvailableActionCalculator.calculate_available_actions(game, big_blind_player.id)

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
        assert game.current_phase == GamePhase.PRE_FLOP

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

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
        game.hand_state.current_phase = GamePhase.FLOP

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

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
        game.hand_state.current_phase = GamePhase.FLOP

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

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
        assert game.current_phase == GamePhase.PRE_FLOP

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

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
        game.hand_state.current_phase = GamePhase.FLOP

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

        action_types = {type(a) for a in result}
        assert AvailableBetAction in action_types
        assert AvailableRaiseAction not in action_types
        bet_actions = [a for a in result if isinstance(a, AvailableBetAction)]
        assert len(bet_actions) == 1
        assert bet_actions[0].min_bet_amount == game.current_blind_level.big_blind
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
        game.hand_state.current_phase = GamePhase.TURN

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

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
        game.hand_state.current_phase = GamePhase.RIVER

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

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
        game.hand_state.current_phase = GamePhase.FLOP

        result = AvailableActionCalculator.calculate_available_actions(game, player.id)

        action_types = {type(a) for a in result}
        assert AvailableBetAction not in action_types
        assert AvailableRaiseAction in action_types
        assert AvailableCallAction in action_types
        assert AvailableFoldAction in action_types
