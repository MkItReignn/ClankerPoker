"""Poker orchestrator with explicit nested loop structure."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.application.poker.context.types import PokerDecisionContext
from src.application.poker.orchestration.state_manager import PokerStateManager
from src.application.poker.records.models import GameRecord
from src.application.protocols.player import (ActionResponse,
                                              AsyncActionProvider)
from src.domain.models.actions import Action
from src.domain.models.available_action import AvailableActions
from src.domain.models.game import Game, GamePhase
from src.domain.models.narration import Narration
from src.logger.factories import get_generic_logger

if TYPE_CHECKING:
    from src.application.poker.events.publisher import FrontEndEventPublisher


@dataclass(frozen=True, slots=True)
class GameResult:
    """Result of a completed game.

    Attributes:
        winner_id: ID of the winning player (or None if cancelled).
        winner_name: Name of the winning player.
        final_state: The final game state.
        record: Complete game record.
        total_hands: Number of hands played.
        total_actions: Total number of actions taken.
    """

    winner_id: str | None
    winner_name: str | None
    final_state: Game
    record: GameRecord | None
    total_hands: int
    total_actions: int


# Type alias for poker action provider
type PokerActionProvider = AsyncActionProvider[
    "PokerDecisionContext",
    list[AvailableActions],
    Action,
    Narration,
]


class PokerOrchestrator:
    """Orchestrates poker games with explicit nested loop structure.

    The orchestrator sequences game logic using three nested loops that
    match poker's natural flow:

        while not state.is_game_complete():           # Game loop
            while not state.is_hand_complete():       # Hand loop
                while not state.is_round_complete():  # Betting round loop
                    get_player_action()
                    state.apply_action()
                state.start_next_round()  # Advance phase (including RIVER -> SHOWDOWN)
            state.resolve_hand()                  # Award pots
            state.mark_game_complete_if_over()    # Check tournament end
            state.start_new_hand()                # If game continues

    Key Design Principles:
    1. Events are published BEFORE state transitions
    2. The state manager manages all state; orchestrator just sequences calls
    3. Each loop level has clear entry/exit points for events
    4. Optional event publisher enables headless mode

    Example:
        ```python
        state = PokerStateManager(config, tournament_config, game_id, seed)
        provider = LLMActionProvider(client)
        publisher = FrontEndEventPublisher(transport)

        orchestrator = PokerOrchestrator(
            state=state,
            action_provider=provider,
            event_publisher=publisher,  # Optional
        )

        result = await orchestrator.run_game()
        print(f"Winner: {result.winner_name}")
        ```
    """

    _logger = get_generic_logger(__name__.removeprefix("src."))

    def __init__(
        self,
        state: PokerStateManager,
        action_provider: PokerActionProvider,
        event_publisher: FrontEndEventPublisher | None = None,
        max_hands: int | None = None,
    ) -> None:
        """Initialize the orchestrator.

        Args:
            state: The poker state manager (manages all game state).
            action_provider: Provider for getting player actions (LLM or bot).
            event_publisher: Optional event publisher for UI updates.
            max_hands: Optional safety limit on number of hands.
        """
        self._state = state
        self._action_provider = action_provider
        self._event_publisher = event_publisher
        self._max_hands = max_hands
        self._total_actions = 0

    async def run_game(self) -> GameResult:
        """Run a complete poker game.

        Returns:
            GameResult with winner and statistics.
        """
        # Initialize game
        self._state.initialize()
        self._total_actions = 0
        hands_played = 0

        # Set up event publisher if provided
        if self._event_publisher is not None:
            self._event_publisher.set_game_id(self._state.game.id)
            self._event_publisher.set_player_names(self._state.player_names)
            self._event_publisher.set_player_configs(self._state._config.player_configs)
            await self._event_publisher.publish_game_started_sequence(self._state.game)

        # ===== GAME LOOP =====
        while not self._state.is_game_complete():
            # Safety limit
            if self._max_hands is not None and hands_played >= self._max_hands:
                self._logger.warning(
                    "Max hands reached, stopping game",
                    max_hands=self._max_hands,
                )
                break

            # Run one complete hand
            await self._run_hand()
            hands_played += 1

            # Start new hand if game continues
            if not self._state.is_game_complete():
                self._state.start_new_hand()
                if self._event_publisher is not None:
                    self._event_publisher.reset_action_counts()

        # Game complete
        winner = self._determine_winner()
        if self._event_publisher is not None:
            await self._event_publisher.publish_game_ended_sequence(
                self._state.game, winner, hands_played
            )

        return GameResult(
            winner_id=winner[0] if winner else None,
            winner_name=winner[1] if winner else None,
            final_state=self._state.game,
            record=self._state.record,
            total_hands=hands_played,
            total_actions=self._total_actions,
        )

    async def _run_hand(self) -> None:
        """Run a single hand to completion."""
        # Publish hand started
        if self._event_publisher is not None:
            await self._event_publisher.publish_hand_started_sequence(self._state.game)

        # ===== HAND LOOP =====
        while not self._state.is_hand_complete():
            # Check for run-out scenario (all players all-in)
            if self._state.game.players.are_all_players_all_in():
                await self._deal_remaining_community_cards()
                break

            # Run betting round
            await self._run_betting_round()

            prev_phase = self._state.game.current_phase
            new_phase = self._state.start_next_round()
            if new_phase is not None and self._event_publisher is not None:
                await self._event_publisher.publish_phase_transition_sequence(
                    self._state.game, prev_phase
                )

        # Publish hand completion BEFORE state transitions
        if self._event_publisher is not None:
            await self._event_publisher.publish_hand_completion_sequence(self._state.game)

        # Resolve hand and check for game completion
        self._state.resolve_hand()
        self._state.mark_game_complete_if_over()

    async def _run_betting_round(self) -> None:
        """Run a single betting round to completion."""
        # ===== BETTING ROUND LOOP =====
        while not self._state.is_round_complete():
            player_id = self._state.get_player_to_act_id()

            if player_id is None:
                raise RuntimeError(
                    "Bug: is_round_complete() returned False but no player to act. "
                    f"Phase: {self._state.game.current_phase}, "
                    f"Players in hand: {len(self._state.game.players_in_hand())}, "
                    f"Position to act: {self._state.game.position_to_act}"
                )

            await self._execute_player_turn(player_id)

    async def _execute_player_turn(self, player_id: str) -> None:
        """Get and apply a single player action."""
        game = self._state.game
        available_actions = self._state.get_available_actions(player_id)

        # Publish player_to_act
        if self._event_publisher is not None:
            await self._event_publisher.on_player_to_act(game, player_id, available_actions)

        # Get action from provider
        context = self._state.build_context(player_id)
        config = self._state.get_player_config(player_id)
        response: ActionResponse[Action, Narration] = await self._action_provider.get_action(
            context, available_actions, config
        )

        turn_result = self._state.apply_action(player_id, response)

        if self._event_publisher is not None:
            await self._event_publisher.on_action_applied(self._state.game, turn_result)

        self._total_actions += 1

    async def _deal_remaining_community_cards(self) -> None:
        """Deal remaining community cards when all players are all-in.

        Advances through FLOP, TURN, RIVER, SHOWDOWN without betting.
        """
        while self._state.game.current_phase != GamePhase.SHOWDOWN:
            prev_phase = self._state.game.current_phase
            self._state.start_next_round()

            if self._event_publisher is not None:
                await self._event_publisher.publish_phase_transition_sequence(
                    self._state.game, prev_phase
                )

    def _determine_winner(self) -> tuple[str, str] | None:
        """Determine the game winner.

        Returns:
            Tuple of (winner_id, winner_name) or None if no clear winner.
        """
        winner = self._state.game.get_winner()
        if winner is None:
            return None

        name = self._state.player_names[winner.id]
        return (winner.id, name)
