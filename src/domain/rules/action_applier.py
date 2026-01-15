from __future__ import annotations

from dataclasses import dataclass, replace

from src.domain.models.actions import Action, ActionType
from src.domain.models.available_action import (AvailableActions,
                                                AvailableAllInAction,
                                                AvailableBetAction,
                                                AvailableCallAction,
                                                AvailableRaiseAction)
from src.domain.models.chips import ChipAmount
from src.domain.models.game import NO_POSITION_TO_ACT, BettingState, Game
from src.domain.models.player import (BettingRoundActionStatus,
                                      HandParticipationStatus, Player,
                                      PlayerId)
from src.domain.models.players import Players
from src.domain.rules.available_action_calculator import \
    AvailableActionCalculator
from src.domain.rules.betting_calculator import BettingCalculator


@dataclass(frozen=True, slots=True)
class _BettingStateUpdate:
    """Tracks betting state changes from applying an action."""

    was_raise: bool
    last_raise_increment: ChipAmount


@dataclass(frozen=True, slots=True)
class _ActionApplicationResult:
    """Result of applying an action to a player.

    Contains the updated player and betting state changes.
    No mutations - purely functional transformation.
    """

    updated_player: Player
    betting_state_update: _BettingStateUpdate


class ActionApplier:
    @staticmethod
    def apply_action(game: Game, player_id: PlayerId, action: Action) -> Game:
        """Apply an action to a player.

        Args:
            game: Current game state
            player_id: ID of the player taking action
            action: The action to apply

        Returns:
            New Game instance with updated state
        """
        player: Player | None = game.players.get_by_id(player_id)
        if player is None:
            raise ValueError(f"Player {player_id} not found in game")

        available_actions: list[AvailableActions] = (
            AvailableActionCalculator.calculate_available_actions(game, player_id)
        )
        ActionApplier._validate_action(action, available_actions)

        players_in_hand: list[Player] = list(game.players.in_hand())
        max_invested: ChipAmount = BettingCalculator.get_max_invested_this_hand(players_in_hand)
        call_amount: ChipAmount = BettingCalculator.calculate_call_amount(
            max_invested, player.total_invested_this_hand
        )

        minimum_raise_increment: ChipAmount = BettingCalculator.calculate_minimum_raise_increment(
            game.betting_state.last_raise_increment,
            game.current_blind_level.big_blind,
        )

        result: _ActionApplicationResult = ActionApplier._apply_action_to_player(
            player, action, call_amount, minimum_raise_increment
        )

        updated_players: Players = game.players.replace_player(player_id, result.updated_player)

        if result.betting_state_update.was_raise:
            updated_players: Players = ActionApplier._reset_acted_players_after_raise(
                updated_players, player_id
            )

        position_to_act: int = ActionApplier._find_next_position_to_act_within_round(
            updated_players, game.betting_state.position_to_act
        )

        updated_betting_state: BettingState = BettingState(
            last_raise_increment=(
                result.betting_state_update.last_raise_increment
                if result.betting_state_update.was_raise
                else game.betting_state.last_raise_increment
            ),
            position_to_act=position_to_act,
        )

        return ActionApplier._build_updated_game(game, updated_players, updated_betting_state)

    @staticmethod
    def _validate_action(action: Action, available_actions: list[AvailableActions]) -> None:
        """Validate that action matches one of the available actions.

        Raises ValueError if action is invalid.
        """
        matching_action = None
        for available_action in available_actions:
            if available_action.action_type == action.action_type:
                matching_action = available_action
                break

        if matching_action is None:
            raise ValueError(
                f"Action {action.action_type.value} is not available. "
                + f"Available actions: {[a.action_type.value for a in available_actions]}"
            )

        if action.action_type == ActionType.CALL:
            if not isinstance(matching_action, AvailableCallAction):
                raise ValueError("Internal error: call action type mismatch")
            if action.amount is not None:
                raise ValueError("Call action cannot have an amount")

        if action.action_type == ActionType.BET:
            if not isinstance(matching_action, AvailableBetAction):
                raise ValueError("Internal error: bet action type mismatch")
            if action.amount is None:
                raise ValueError("Bet action requires an amount")
            if action.amount.value < matching_action.min_bet_amount.value:
                raise ValueError(
                    f"Bet amount {action.amount.value} is below minimum "
                    + f"{matching_action.min_bet_amount.value}"
                )
            if action.amount.value > matching_action.max_bet_amount.value:
                raise ValueError(
                    f"Bet amount {action.amount.value} exceeds maximum "
                    + f"{matching_action.max_bet_amount.value}"
                )

        if action.action_type == ActionType.RAISE:
            if not isinstance(matching_action, AvailableRaiseAction):
                raise ValueError("Internal error: raise action type mismatch")
            if action.amount is None:
                raise ValueError("Raise action requires an amount")
            if action.amount.value < matching_action.min_raise_amount.value:
                raise ValueError(
                    f"Raise amount {action.amount.value} is below minimum "
                    + f"{matching_action.min_raise_amount.value}"
                )
            if action.amount.value > matching_action.max_raise_amount.value:
                raise ValueError(
                    f"Raise amount {action.amount.value} exceeds maximum "
                    + f"{matching_action.max_raise_amount.value}"
                )

        if action.action_type == ActionType.ALL_IN:
            if not isinstance(matching_action, AvailableAllInAction):
                raise ValueError("Internal error: all-in action type mismatch")
            if action.amount is None:
                raise ValueError("All-in action requires an amount")
            if action.amount.value != matching_action.all_in_amount.value:
                raise ValueError(
                    f"All-in amount {action.amount.value} does not match "
                    + f"player's remaining chips {matching_action.all_in_amount.value}"
                )

    @staticmethod
    def _apply_action_to_player(
        player: Player,
        action: Action,
        call_amount: ChipAmount,
        minimum_raise_increment: ChipAmount,
    ) -> _ActionApplicationResult:
        """Apply action to player and return result with updated player and betting state changes."""
        if action.action_type == ActionType.FOLD:
            return ActionApplier._apply_fold(player)
        elif action.action_type == ActionType.CHECK:
            return ActionApplier._apply_check(player)
        elif action.action_type == ActionType.CALL:
            return ActionApplier._apply_call(player, call_amount)
        elif action.action_type == ActionType.BET:
            return ActionApplier._apply_bet(player, action)
        elif action.action_type == ActionType.RAISE:
            return ActionApplier._apply_raise(player, action, call_amount)
        elif action.action_type == ActionType.ALL_IN:
            return ActionApplier._apply_all_in(player, action, call_amount, minimum_raise_increment)
        else:
            raise ValueError(f"Unknown action type: {action.action_type}")

    @staticmethod
    def _apply_fold(player: Player) -> _ActionApplicationResult:
        """Apply fold action: player exits hand, clears cards."""
        updated_player = replace(
            player,
            participation_status=HandParticipationStatus.FOLDED,
            betting_status=BettingRoundActionStatus.ACTED,
            hole_cards=None,
        )
        return _ActionApplicationResult(
            updated_player=updated_player,
            betting_state_update=_BettingStateUpdate(
                was_raise=False,
                last_raise_increment=ChipAmount(0),
            ),
        )

    @staticmethod
    def _apply_check(player: Player) -> _ActionApplicationResult:
        """Apply check action: player acts without betting."""
        updated_player = replace(
            player,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        return _ActionApplicationResult(
            updated_player=updated_player,
            betting_state_update=_BettingStateUpdate(
                was_raise=False,
                last_raise_increment=ChipAmount(0),
            ),
        )

    @staticmethod
    def _apply_call(player: Player, call_amount: ChipAmount) -> _ActionApplicationResult:
        """Apply call action: player matches current bet level."""
        chips_to_call = min(call_amount.value, player.remaining_chips.value)
        updated_player = replace(
            player,
            remaining_chips=player.remaining_chips - ChipAmount(chips_to_call),
            total_invested_this_hand=player.total_invested_this_hand + ChipAmount(chips_to_call),
            betting_status=BettingRoundActionStatus.ACTED,
        )
        return _ActionApplicationResult(
            updated_player=updated_player,
            betting_state_update=_BettingStateUpdate(
                was_raise=False,
                last_raise_increment=ChipAmount(0),
            ),
        )

    @staticmethod
    def _apply_bet(player: Player, action: Action) -> _ActionApplicationResult:
        """Apply bet action: player bets when no bet exists.

        Amount is the total bet amount (not an increment).
        """
        if action.amount is None:
            raise ValueError("Bet action requires an amount")

        bet_amount = action.amount
        updated_player = replace(
            player,
            remaining_chips=player.remaining_chips - bet_amount,
            total_invested_this_hand=player.total_invested_this_hand + bet_amount,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        return _ActionApplicationResult(
            updated_player=updated_player,
            betting_state_update=_BettingStateUpdate(
                was_raise=True,
                last_raise_increment=bet_amount,
            ),
        )

    @staticmethod
    def _apply_raise(
        player: Player, action: Action, call_amount: ChipAmount
    ) -> _ActionApplicationResult:
        """Apply raise action: player calls then raises by increment."""
        if action.amount is None:
            raise ValueError("Raise action requires an amount")

        raise_increment = action.amount
        total_needed = ChipAmount(call_amount.value + raise_increment.value)
        updated_player = replace(
            player,
            remaining_chips=player.remaining_chips - total_needed,
            total_invested_this_hand=player.total_invested_this_hand + total_needed,
            betting_status=BettingRoundActionStatus.ACTED,
        )
        return _ActionApplicationResult(
            updated_player=updated_player,
            betting_state_update=_BettingStateUpdate(
                was_raise=True,
                last_raise_increment=raise_increment,
            ),
        )

    @staticmethod
    def _apply_all_in(
        player: Player,
        action: Action,
        call_amount: ChipAmount,
        minimum_raise_increment: ChipAmount,
    ) -> _ActionApplicationResult:
        """Apply all-in action: player bets all remaining chips.

        All-in reopening rules:
        - If call_amount == 0: equivalent to BET (post-flop) or RAISE (pre-flop), always reopens action
        - If all_in_amount < call_amount: treated as partial call, does not reopen
        - If all_in_amount == call_amount: treated as call, does not reopen
        - If all_in_amount > call_amount but raise_increment < minimum_raise_increment:
          treated as call, does not reopen
        - If all_in_amount > call_amount and raise_increment >= minimum_raise_increment:
          treated as raise, reopens action
        """
        if action.amount is None:
            raise ValueError("All-in action requires an amount")

        all_in_amount = action.amount
        updated_player = replace(
            player,
            remaining_chips=player.remaining_chips - all_in_amount,
            total_invested_this_hand=player.total_invested_this_hand + all_in_amount,
            betting_status=BettingRoundActionStatus.ACTED,
        )

        if call_amount.value == 0:
            return _ActionApplicationResult(
                updated_player=updated_player,
                betting_state_update=_BettingStateUpdate(
                    was_raise=True,
                    last_raise_increment=all_in_amount,
                ),
            )

        if all_in_amount < call_amount:
            raise_increment = ChipAmount(0)
        else:
            raise_increment = all_in_amount - call_amount

        is_raise = raise_increment.value > 0 and raise_increment >= minimum_raise_increment

        return _ActionApplicationResult(
            updated_player=updated_player,
            betting_state_update=_BettingStateUpdate(
                was_raise=is_raise,
                last_raise_increment=raise_increment if is_raise else ChipAmount(0),
            ),
        )

    @staticmethod
    def _reset_acted_players_after_raise(players: Players, raising_player_id: str) -> Players:
        """Reset all acted players to NEEDS_ACTION after a raise.

        Returns new Players collection without mutating original.
        """
        return players.transform_filtered(
            predicate=lambda p: (
                p.is_in_hand()
                and p.id != raising_player_id
                and p.betting_status == BettingRoundActionStatus.ACTED
            ),
            transform=lambda p: replace(p, betting_status=BettingRoundActionStatus.NEEDS_ACTION),
        )

    @staticmethod
    def _build_updated_game(
        game: Game, updated_players: Players, updated_betting_state: BettingState
    ) -> Game:
        """Build new Game instance with updated players and betting state."""
        return Game(
            identity=game.identity,
            tournament_config=game.tournament_config,
            hand_state=game.hand_state,
            pot_state=game.pot_state,
            betting_state=updated_betting_state,
            button_seat=game.button_seat,
            blind_state=game.blind_state,
            players=updated_players,
            results=game.results,
        )

    @staticmethod
    def _find_next_position_to_act_within_round(players: Players, last_position_to_act: int) -> int:
        """Find next player who needs action within the current betting round, starting from last_position_to_act.

        This method is used to find the next player to act after someone has taken an action
        within an ongoing betting round. It searches circularly starting from the position
        after last_position_to_act.

        Returns NO_POSITION_TO_ACT if no player needs action or last_position_to_act is invalid.
        """
        if last_position_to_act == NO_POSITION_TO_ACT:
            return NO_POSITION_TO_ACT

        num_players: int = len(players)
        start_pos: int = (last_position_to_act + 1) % num_players

        for i in range(num_players):
            position: int = (start_pos + i) % num_players
            player: Player = players[position]
            if player.betting_status == BettingRoundActionStatus.NEEDS_ACTION:
                return position

        return NO_POSITION_TO_ACT
