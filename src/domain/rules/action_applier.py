from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from src.domain.models.actions import Action, ActionType
from src.domain.models.available_action import (AvailableActions,
                                                AvailableAllInAction,
                                                AvailableBetAction,
                                                AvailableCallAction,
                                                AvailableRaiseAction)
from src.domain.models.chips import ChipAmount
from src.domain.models.game import NO_CURRENT_PLAYER, BettingState, Game
from src.domain.models.player import (BettingRoundActionStatus,
                                      HandParticipationStatus, Player)
from src.domain.rules.available_action_calculator import \
    AvailableActionCalculator
from src.domain.rules.betting_calculator import BettingCalculator


class ActionApplier:
    @staticmethod
    def apply_action(game: Game, player: Player, action: Action) -> Game:
        available_actions = AvailableActionCalculator.calculate_available_actions(game, player)
        ActionApplier._validate_action(action, available_actions)

        updated_players: list[Player] = deepcopy(game.players)
        player_index: int = ActionApplier._find_player_index(updated_players, player.id)
        updated_player: Player = updated_players[player_index]

        players_in_hand = [p for p in updated_players if p.is_in_hand()]
        max_invested: ChipAmount = BettingCalculator.get_max_invested_this_hand(players_in_hand)
        call_amount: ChipAmount = BettingCalculator.calculate_call_amount(
            max_invested, updated_player.total_invested_this_hand
        )

        minimum_raise_increment: ChipAmount = BettingCalculator.calculate_minimum_raise_increment(
            game.betting_state.last_raise_increment,
            game.current_blind_level.big_blind,
        )

        betting_state_update: _BettingStateUpdate = ActionApplier._apply_action_to_player(
            updated_player, action, call_amount, minimum_raise_increment
        )

        updated_players[player_index] = updated_player

        if betting_state_update.was_raise:
            ActionApplier._reset_acted_players_after_raise(updated_players, updated_player.id)

        current_player_position: int = ActionApplier._find_next_player_needing_action_within_round(
            updated_players, game.betting_state.current_player_position
        )

        updated_betting_state: BettingState = BettingState(
            last_raise_increment=(
                betting_state_update.last_raise_increment
                if betting_state_update.was_raise
                else game.betting_state.last_raise_increment
            ),
            current_player_position=current_player_position,
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
    def _find_player_index(players: list[Player], player_id: str) -> int:
        """Find player index by ID, raising if not found."""
        for i, p in enumerate(players):
            if p.id == player_id:
                return i
        raise ValueError(f"Player {player_id} not found in game")

    @staticmethod
    def _apply_action_to_player(
        player: Player,
        action: Action,
        call_amount: ChipAmount,
        minimum_raise_increment: ChipAmount,
    ) -> _BettingStateUpdate:
        """Apply action to player and return betting state changes."""
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
    def _apply_fold(player: Player) -> _BettingStateUpdate:
        """Apply fold action: player exits hand, clears cards."""
        player.participation_status = HandParticipationStatus.FOLDED
        player.betting_status = BettingRoundActionStatus.ACTED
        player.hole_cards = None
        return _BettingStateUpdate(
            was_raise=False,
            last_raise_increment=ChipAmount(0),
        )

    @staticmethod
    def _apply_check(player: Player) -> _BettingStateUpdate:
        """Apply check action: player acts without betting."""
        player.betting_status = BettingRoundActionStatus.ACTED
        return _BettingStateUpdate(
            was_raise=False,
            last_raise_increment=ChipAmount(0),
        )

    @staticmethod
    def _apply_call(player: Player, call_amount: ChipAmount) -> _BettingStateUpdate:
        """Apply call action: player matches current bet level."""
        chips_to_call = min(call_amount.value, player.remaining_chips.value)
        ActionApplier._update_player_bet(player, ChipAmount(chips_to_call))
        player.betting_status = BettingRoundActionStatus.ACTED
        return _BettingStateUpdate(
            was_raise=False,
            last_raise_increment=ChipAmount(0),
        )

    @staticmethod
    def _apply_bet(player: Player, action: Action) -> _BettingStateUpdate:
        """Apply bet action: player bets when no bet exists.

        Amount is the total bet amount (not an increment).
        """
        if action.amount is None:
            raise ValueError("Bet action requires an amount")

        bet_amount = action.amount
        ActionApplier._update_player_bet(player, bet_amount)
        player.betting_status = BettingRoundActionStatus.ACTED

        raise_increment = bet_amount

        return _BettingStateUpdate(
            was_raise=True,
            last_raise_increment=raise_increment,
        )

    @staticmethod
    def _apply_raise(
        player: Player, action: Action, call_amount: ChipAmount
    ) -> _BettingStateUpdate:
        """Apply raise action: player calls then raises by increment."""
        if action.amount is None:
            raise ValueError("Raise action requires an amount")

        raise_increment = action.amount
        total_needed = call_amount.value + raise_increment.value
        ActionApplier._update_player_bet(player, ChipAmount(total_needed))
        player.betting_status = BettingRoundActionStatus.ACTED

        return _BettingStateUpdate(
            was_raise=True,
            last_raise_increment=raise_increment,
        )

    @staticmethod
    def _apply_all_in(
        player: Player,
        action: Action,
        call_amount: ChipAmount,
        minimum_raise_increment: ChipAmount,
    ) -> _BettingStateUpdate:
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
        ActionApplier._update_player_bet(player, all_in_amount)
        player.betting_status = BettingRoundActionStatus.ACTED

        if call_amount.value == 0:
            return _BettingStateUpdate(
                was_raise=True,
                last_raise_increment=all_in_amount,
            )

        if all_in_amount < call_amount:
            raise_increment = ChipAmount(0)
        else:
            raise_increment = all_in_amount - call_amount

        is_raise = raise_increment.value > 0 and raise_increment >= minimum_raise_increment

        return _BettingStateUpdate(
            was_raise=is_raise,
            last_raise_increment=raise_increment if is_raise else ChipAmount(0),
        )

    @staticmethod
    def _update_player_bet(player: Player, amount: ChipAmount) -> None:
        """Update player's chips and total invested."""
        player.remaining_chips = player.remaining_chips - amount
        player.total_invested_this_hand = player.total_invested_this_hand + amount

    @staticmethod
    def _reset_acted_players_after_raise(players: list[Player], raising_player_id: str) -> None:
        """Reset all acted players to NEEDS_ACTION after a raise."""
        for player in players:
            if (
                player.is_in_hand()
                and player.id != raising_player_id
                and player.betting_status == BettingRoundActionStatus.ACTED
            ):
                player.betting_status = BettingRoundActionStatus.NEEDS_ACTION

    @staticmethod
    def _build_updated_game(
        game: Game, updated_players: list[Player], updated_betting_state: BettingState
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
    def _find_next_player_needing_action_within_round(
        players: list[Player], current_position: int
    ) -> int:
        """Find next player who needs action within the current betting round, starting from current_position.

        This method is used to find the next player to act after someone has taken an action
        within an ongoing betting round. It searches circularly starting from the position
        after current_position.

        Returns NO_CURRENT_PLAYER if no player needs action or current_position is invalid.
        """
        if current_position == NO_CURRENT_PLAYER:
            return NO_CURRENT_PLAYER

        num_players: int = len(players)
        start_pos: int = (current_position + 1) % num_players

        for i in range(num_players):
            position: int = (start_pos + i) % num_players
            player: Player = players[position]
            if player.betting_status == BettingRoundActionStatus.NEEDS_ACTION:
                return position

        return NO_CURRENT_PLAYER


@dataclass(frozen=True, slots=True)
class _BettingStateUpdate:
    """Tracks betting state changes from applying an action."""

    was_raise: bool
    last_raise_increment: ChipAmount
