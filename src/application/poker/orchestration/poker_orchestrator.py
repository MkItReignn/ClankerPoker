"""Poker orchestrator with explicit nested loop structure."""

import asyncio
from dataclasses import dataclass

from src.application.poker.context import PokerDecisionContext
from src.application.poker.orchestration.state_manager import PokerStateManager
from src.application.poker.records.models import GameRecord
from src.application.protocols.player import (
    ActionResponse,
    AsyncActionProvider,
)
from src.domain.models.actions import Action
from src.domain.models.available_action import AvailableActions
from src.domain.models.game import Game, HandPhase
from src.domain.models.narration import Narration
from src.logger.factories import get_generic_logger

type PokerActionProvider = AsyncActionProvider[
    PokerDecisionContext,
    list[AvailableActions],
    Action,
    Narration,
]


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
    1. The state manager manages all state; orchestrator just sequences calls
    2. Each loop level has clear entry/exit points

    Example:
        ```python
        state = PokerStateManager(config, tournament_config, game_id, seed)
        provider = LLMActionProvider(client)

        orchestrator = PokerOrchestrator(state=state, action_provider=provider)

        result = await orchestrator.run_game()
        print(f"Winner: {result.winner_name}")
        ```
    """

    _logger = get_generic_logger(__name__.removeprefix("src."))

    def __init__(
        self,
        state: PokerStateManager,
        action_provider: PokerActionProvider,
        max_hands: int | None = None,
        shutdown_event: asyncio.Event | None = None,
    ) -> None:
        self._state = state
        self._action_provider = action_provider
        self._max_hands = max_hands
        self._shutdown_event = shutdown_event
        self._total_actions = 0

    async def run_game(self) -> GameResult:
        """Run a complete poker game.

        Returns:
            GameResult with winner and statistics.
        """
        async with self._action_provider:
            await self._state.initialize()
            self._total_actions = 0
            hands_played = 0

            # ===== GAME LOOP =====
            while not self._state.is_game_complete():
                if self._shutdown_event and self._shutdown_event.is_set():
                    self._logger.info("Shutdown requested, stopping game")
                    break

                # Safety limit
                if (
                    self._max_hands is not None
                    and hands_played >= self._max_hands
                ):
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
                    await self._state.start_new_hand()

            winner = self._determine_winner()

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
        # ===== HAND LOOP =====
        while not self._state.is_hand_complete():
            if self._shutdown_event and self._shutdown_event.is_set():
                return

            # Check for run-out scenario (all players all-in)
            if self._state.game.players.are_all_players_all_in():
                await self._deal_remaining_community_cards()
                break

            # Run betting round
            await self._run_betting_round()

            await self._state.start_next_round()

        # Resolve hand and check for game completion
        await self._state.resolve_hand()
        await self._state.mark_game_complete_if_over()

    async def _run_betting_round(self) -> None:
        """Run a single betting round to completion."""
        # ===== BETTING ROUND LOOP =====
        while not self._state.is_round_complete():
            if self._shutdown_event and self._shutdown_event.is_set():
                return

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
        available_actions = self._state.get_available_actions(player_id)
        context = self._state.build_context(player_id)
        config = self._state.get_player_config(player_id)

        response: ActionResponse[Action, Narration] = (
            await self._action_provider.get_action(
                context, available_actions, config
            )
        )

        await self._state.apply_action(player_id, response)
        self._total_actions += 1

    async def _deal_remaining_community_cards(self) -> None:
        """Deal remaining community cards when all players are all-in."""
        while self._state.game.current_phase != HandPhase.SHOWDOWN:
            await self._state.start_next_round()

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
