"""History recorder for capturing game state snapshots."""

from __future__ import annotations

from datetime import datetime

from src.application.poker.history.models import (
    ActionRecord,
    GameHistory,
    GameMetadata,
    HandLevelPlayerState,
    HandOutcome,
    PlayerOutcome,
    RoundHistory,
    RoundLevelPlayerState,
    ShowdownResult,
    TurnHistory,
    TurnLevelPlayerState,
)
from src.domain.models.actions import Action
from src.domain.models.chips import ChipAmount
from src.domain.models.game import Game, GamePhase
from src.domain.models.player import HandParticipationStatus, Player
from src.domain.models.position import PositionName, TablePositionMapping
from src.domain.rules.betting_calculator import BettingCalculator
from src.domain.rules.hand_evaluator import HandEvaluator
from src.domain.rules.position_manager import PositionManager
from src.logger.factories import get_generic_logger


class HistoryRecorder:
    """Records game history snapshots at each level of the game hierarchy.

    Responsible for capturing state snapshots and building history objects:
    - Game level: tournament metadata and player registration
    - Hand level: player positions, hole cards, blinds
    - Round level: player states at start of each betting round
    - Turn level: individual actions with pot changes
    """

    def __init__(self, player_names: dict[str, str]) -> None:
        """Initialize the history recorder.

        Args:
            player_names: Dictionary mapping player_id to display name.
        """
        self._player_names = player_names
        self._history: GameHistory | None = None
        self._logger = get_generic_logger(__name__.removeprefix("src."))

    @property
    def history(self) -> GameHistory | None:
        """Get the current game history."""
        return self._history

    def _get_player_name(self, player_id: str) -> str:
        if player_id not in self._player_names:
            self._logger.error(
                "Player ID not found in player_names",
                player_id=player_id,
                available_player_ids=list(self._player_names.keys()),
            )
            raise KeyError(f"Player ID '{player_id}' not found in player_names")
        return self._player_names[player_id]

    # =========================================================================
    # Game Lifecycle
    # =========================================================================

    def initialize_history(self, state: Game, metadata: GameMetadata) -> None:
        """Initialize game history with metadata and register all players.

        Args:
            state: Current game state with players.
            metadata: Tournament configuration metadata.
        """
        self._history = GameHistory(state.id, metadata)

        # Register all players with initial state
        for player in state.players:
            player_name = self._get_player_name(player.id)
            self._history.register_player(
                player_id=player.id,
                name=player_name,
                initial_chips=player.remaining_chips,
                seat=player.seat,
            )

    def complete_game(self, completed_at: datetime) -> None:
        """Mark the game as complete.

        Args:
            completed_at: Timestamp when game completed.
        """
        if self._history is not None:
            self._history.metadata.completed_at = completed_at

    # =========================================================================
    # Hand Lifecycle
    # =========================================================================

    def record_hand_start(self, state: Game) -> None:
        """Record the start of a new hand.

        Creates HandLevelPlayerState for each active player and starts
        the hand in history.

        Args:
            state: Game state after hand initialization.
        """
        if self._history is None:
            return

        # Capture hand-level player states
        hand_player_states: dict[str, HandLevelPlayerState] = {}
        position_mapping: TablePositionMapping = PositionManager.resolve_positions_for_hand(
            all_players=list(state.players),
            previous_button_seat=state.button_seat,
            advance_button=False,  # Reading current state for history
        )

        for player in state.players:
            if player.participation_status != HandParticipationStatus.ELIMINATED:
                # Get position name for this player
                position_name: PositionName | None = position_mapping.get_position_for_seat(
                    player.seat
                )
                player_name: str = self._get_player_name(player.id)

                hand_player_states[player.id] = HandLevelPlayerState(
                    player_id=player.id,
                    player_name=player_name,
                    seat=player.seat,
                    chips=player.remaining_chips,
                    hole_cards=player.hole_cards,
                    position=position_name,
                    starting_chips=player.remaining_chips,
                    total_invested_in_hand=ChipAmount(0),  # Hand just started
                )

        # Start the hand
        self._history.start_hand(
            hand_number=state.hand_state.hand_number,
            button_seat=state.button_seat,
            blinds=state.current_blind_level,
            player_states=hand_player_states,
        )

    def record_hand_complete(self, state: Game) -> None:
        """Record the completion of a hand.

        Builds the hand outcome and completes the hand in history.

        Args:
            state: Game state after hand completion.
        """
        if self._history is None or self._history.current_hand is None:
            return

        outcome: HandOutcome = self._build_hand_outcome(state)
        self._history.complete_hand(outcome)

    # =========================================================================
    # Round Lifecycle
    # =========================================================================

    def record_round_start(self, state: Game) -> None:
        """Record the start of a betting round.

        Creates RoundLevelPlayerState for each player and starts
        the round in history.

        Args:
            state: Current game state at round start.
        """
        if self._history is None or self._history.current_hand is None:
            return

        # Capture round-level player states
        round_player_states: dict[str, RoundLevelPlayerState] = {}

        for player in state.players:
            # Determine participation status
            if player.participation_status == HandParticipationStatus.ELIMINATED:
                participation_status = HandParticipationStatus.ELIMINATED
            elif player.participation_status == HandParticipationStatus.FOLDED:
                participation_status = HandParticipationStatus.FOLDED
            else:
                participation_status = HandParticipationStatus.IN_HAND

            # Calculate total invested in hand so far
            total_invested = ChipAmount(0)
            if player.stack_at_hand_start is not None:
                total_invested = ChipAmount(
                    player.stack_at_hand_start.value - player.remaining_chips.value
                )

            # Calculate total invested in this round
            total_invested_in_round = ChipAmount(0)
            if len(self._history.current_hand.rounds) > 0:
                # Get the last completed round (current round hasn't been added yet)
                previous_round = self._history.current_hand.rounds[-1]

                if player.id in previous_round.player_states:
                    previous_total = previous_round.player_states[player.id].total_invested_in_hand
                    total_invested_in_round = ChipAmount(
                        total_invested.value - previous_total.value
                    )
                else:
                    # First round (preflop) - total_invested is the round investment
                    total_invested_in_round = total_invested
            else:
                # First round (preflop) - total_invested is the round investment
                total_invested_in_round = total_invested

            player_name = self._get_player_name(player.id)
            round_player_states[player.id] = RoundLevelPlayerState(
                player_id=player.id,
                player_name=player_name,
                seat=player.seat,
                chips=player.remaining_chips,
                chips_at_round_start=player.remaining_chips,
                total_invested_in_hand=total_invested,
                total_invested_in_round=total_invested_in_round,
                participation_status=participation_status,
                is_all_in=player.is_all_in(),
            )

        # Get community cards (may be empty for preflop, or 5 cards if dealt upfront)
        community_cards = tuple(state.community_cards) if state.community_cards else ()

        # Start the round
        self._history.current_hand.start_round(
            phase=state.current_phase,
            community_cards=community_cards,
            player_states=round_player_states,
        )

    def record_round_complete(self) -> None:
        """Record the completion of a betting round."""
        if self._history is None or self._history.current_hand is None:
            return

        current_round = self._history.current_hand.current_round()
        if current_round is not None and not current_round.is_complete:
            current_round.complete()

    # =========================================================================
    # Action Recording
    # =========================================================================

    def record_action(
        self,
        state_before: Game,
        state_after: Game,
        player_id: str,
        action: Action,
    ) -> None:
        """Record an action taken by a player.

        Creates TurnLevelPlayerState (before action), ActionRecord,
        and TurnHistory with pot changes.

        Args:
            state_before: Game state before the action.
            state_after: Game state after the action.
            player_id: ID of player who acted.
            action: The action taken.
        """
        if self._history is None or self._history.current_hand is None:
            return

        current_round: RoundHistory | None = self._history.current_hand.current_round()
        if current_round is None:
            return

        player: Player | None = state_before.players.get_by_id(player_id)
        if player is None:
            return

        player_name = self._get_player_name(player_id)

        # Capture state BEFORE action
        chips_before: int = player.remaining_chips.value
        pot_before: int = state_before.pot.value
        current_bet_before: int = BettingCalculator.get_max_invested_this_hand(
            state_before.players_in_hand()
        ).value
        invested_before: int = (
            player.stack_at_hand_start.value - player.remaining_chips.value
            if player.stack_at_hand_start is not None
            else 0
        )

        # Capture state AFTER action
        pot_after: int = state_after.pot.value
        current_bet_after: int = BettingCalculator.get_max_invested_this_hand(
            state_after.players_in_hand()
        ).value

        # Create turn-level player state (BEFORE action)
        turn_player_state: TurnLevelPlayerState = TurnLevelPlayerState(
            player_id=player_id,
            player_name=player_name,
            seat=player.seat,
            chips=ChipAmount(chips_before),
            total_invested_before_action=ChipAmount(invested_before),
            can_raise=player.can_raise,
        )

        # Create action record
        action_record: ActionRecord = ActionRecord(
            player_id=player_id,
            player_name=player_name,
            phase=state_before.current_phase,
            action_type=action.action_type,
            amount=action.amount,
            timestamp=datetime.now(),
        )

        # Create turn history
        turn_number: int = len(current_round.turns) + 1
        turn_history: TurnHistory = TurnHistory(
            turn_number=turn_number,
            player_state=turn_player_state,
            action=action_record,
            timestamp=datetime.now(),
            pot_before=ChipAmount(pot_before),
            pot_after=ChipAmount(pot_after),
            current_bet_before=ChipAmount(current_bet_before),
            current_bet_after=ChipAmount(current_bet_after),
        )

        # Add turn to current round
        current_round.add_turn(turn_history)

    # =========================================================================
    # Private Helpers
    # =========================================================================

    def _build_hand_outcome(self, state: Game) -> HandOutcome:
        """Build hand outcome from game state.

        Args:
            state: Game state after hand completion.

        Returns:
            HandOutcome with winners, showdown results, and player outcomes.
        """
        # Get winners from results
        winner_ids: list[str] = []
        total_pot: ChipAmount = state.pot

        if state.results is not None:
            winner_ids = [w[0] for w in state.results.winners]
            # Sum up all winnings for pot total if available
            if state.results.winners:
                total_pot = sum((w[1] for w in state.results.winners), start=ChipAmount(0))

        # Determine if showdown
        players_in_hand = state.players_in_hand()
        was_showdown = len(players_in_hand) > 1 and state.current_phase == GamePhase.SHOWDOWN

        # Build showdown results
        showdown_results: list[ShowdownResult] = []
        if was_showdown:
            community_cards = state.community_cards
            if len(community_cards) != 5:
                raise ValueError(
                    f"Showdown requires exactly 5 community cards, got {len(community_cards)}"
                )
            for player in players_in_hand:
                if player.hole_cards is not None:
                    hand_evaluation = HandEvaluator.evaluate_hand_strength(
                        player.hole_cards, community_cards
                    )
                    showdown_results.append(
                        ShowdownResult(
                            player_id=player.id,
                            player_name=self._get_player_name(player.id),
                            hole_cards=player.hole_cards,
                            hand_evaluation=hand_evaluation,
                        )
                    )

        # Build player outcomes
        player_outcomes: list[PlayerOutcome] = []
        for player in state.players:
            if player.participation_status == HandParticipationStatus.ELIMINATED:
                continue

            chips_won = ChipAmount(0)
            chips_lost = ChipAmount(0)

            if player.id in winner_ids and state.results is not None:
                for w_id, w_amount in state.results.winners:
                    if w_id == player.id:
                        chips_won = w_amount

            # Check if player was eliminated this hand
            was_eliminated_this_hand = (
                player.remaining_chips.value == 0
                and player.participation_status != HandParticipationStatus.FOLDED
            )
            player_outcomes.append(
                PlayerOutcome(
                    player_id=player.id,
                    player_name=self._get_player_name(player.id),
                    chips_won=chips_won,
                    chips_lost=chips_lost,
                    final_stack=player.remaining_chips,
                    was_eliminated=was_eliminated_this_hand,
                )
            )

        return HandOutcome(
            winner_ids=tuple(winner_ids) if winner_ids else ("unknown",),
            pot_amount=ChipAmount(max(total_pot.value, 1)),  # Ensure positive
            was_showdown=was_showdown,
            showdown_results=tuple(showdown_results),
            player_outcomes=tuple(player_outcomes),
        )
