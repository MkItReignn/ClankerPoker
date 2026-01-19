"""Poker tournament orchestrator for running complete poker tournaments."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from src.application.poker.context.types import PokerDecisionContext
from src.application.poker.history.models import GameHistory
from src.application.protocols.history import GameHistoryRepository
from src.application.protocols.player import ActionResponse, AsyncActionProvider, PlayerConfig
from src.application.use_cases.game_runner import TurnResult
from src.application.poker.orchestration.runner import PokerGameRunner
from src.domain.models.actions import Action
from src.domain.models.available_action import AvailableActions
from src.domain.models.game import Game
from src.domain.models.narration import Narration
from src.domain.models.player import Player
from src.logger.factories import get_generic_logger


@dataclass(frozen=True, slots=True)
class TournamentResult:
    """Result of a completed tournament.

    Attributes:
        winner_id: ID of the winning player (or None if cancelled).
        winner_name: Name of the winning player.
        final_state: The final game state.
        history: Complete game history.
        total_hands: Number of hands played.
        total_actions: Total number of actions taken.
    """

    winner_id: str | None
    winner_name: str | None
    final_state: Game
    history: GameHistory | None
    total_hands: int
    total_actions: int


# Type alias for poker action provider
type PokerActionProvider = AsyncActionProvider[
    "PokerDecisionContext",
    list[AvailableActions],
    Action,
    Narration,
]

# Type alias for hand complete callback
type HandCompleteCallback = Callable[[Game, int], None]


class PokerTournamentOrchestrator:
    """Orchestrates complete poker tournaments.

    Coordinates the poker game runner, action providers, and persistence
    to run tournaments from start to finish.

    This class is poker-specific and uses PokerGameRunner, PokerDecisionContext,
    and poker-specific terminology (hands, blinds, etc.).

    Features:
    - Runs complete poker tournaments with any action provider
    - Persists history after each hand (optional)
    - Emits events for real-time updates (optional)
    - Handles game state transitions
    - Tracks tournament statistics

    Example:
        ```python
        runner = PokerGameRunner(config)
        provider = BotActionProvider()
        repository = JsonGameHistoryRepository()

        orchestrator = PokerTournamentOrchestrator(
            runner=runner,
            action_provider=provider,
            repository=repository,
        )

        game = GameFactory.create_tournament(players, tournament_config)
        result = await orchestrator.run_tournament(game)
        print(f"Winner: {result.winner_name}")
        ```
    """

    _logger = get_generic_logger(__name__.removeprefix("src."))

    def __init__(
        self,
        runner: PokerGameRunner,
        action_provider: PokerActionProvider,
        repository: GameHistoryRepository[GameHistory] | None = None,
        on_hand_complete: HandCompleteCallback | None = None,
        persist_after_each_hand: bool = True,
    ) -> None:
        """Initialize the tournament orchestrator.

        Args:
            runner: The poker game runner.
            action_provider: Provider for getting player actions.
            repository: Optional repository for persisting history.
            on_hand_complete: Optional callback when a hand completes.
            persist_after_each_hand: Whether to persist after each hand.
        """
        self._runner: PokerGameRunner = runner
        self._action_provider: PokerActionProvider = action_provider
        self._repository: GameHistoryRepository[GameHistory] | None = repository
        self._on_hand_complete: HandCompleteCallback | None = on_hand_complete
        self._persist_after_each_hand: bool = persist_after_each_hand
        self._total_actions: int = 0

    async def run_tournament(
        self,
        initial_game: Game,
        max_hands: int | None = None,
    ) -> TournamentResult:
        """Run a complete tournament.

        Args:
            initial_game: The initial game state (not yet started).
            max_hands: Optional maximum number of hands (safety limit).

        Returns:
            TournamentResult with winner and statistics.
        """
        self._total_actions = 0

        # Initialize the game (deals first hand)
        game = self._runner.initialize_game(initial_game)
        self._logger.info(
            "Tournament started",
            game_id=game.id,
            players=len(game.players),
        )

        hands_played = 0
        last_hand_number = 0

        # Main game loop
        while not self._runner.is_game_over(game):
            # Safety limit
            if max_hands is not None and hands_played >= max_hands:
                self._logger.warning(
                    "Max hands reached, stopping tournament",
                    max_hands=max_hands,
                )
                break

            # Check if we need someone to act
            player_id = self._runner.get_current_player_id(game)

            if player_id is None:
                # No player to act - advance game phase
                prev_hand = game.hand_state.hand_number
                game = self._runner.advance_game_phase(game)

                # Check if hand completed
                if game.hand_state.hand_number != prev_hand or game.is_hand_complete():
                    if prev_hand != last_hand_number:
                        hands_played += 1
                        last_hand_number = prev_hand
                        self._on_hand_completed(game, prev_hand)
                continue

            # Get action from provider
            game = await self._process_player_turn(game, player_id)

        # Tournament complete
        winner: tuple[str, str] | None = self._determine_winner(game)
        self._persist_final()

        self._logger.info(
            "Tournament completed",
            game_id=game.id,
            winner=winner[0] if winner else None,
            hands_played=hands_played,
            total_actions=self._total_actions,
        )

        return TournamentResult(
            winner_id=winner[0] if winner else None,
            winner_name=winner[1] if winner else None,
            final_state=game,
            history=self._runner.history,
            total_hands=hands_played,
            total_actions=self._total_actions,
        )

    async def _process_player_turn(self, game: Game, player_id: str) -> Game:
        """Process a single player's turn.

        Args:
            game: Current game state.
            player_id: ID of player who needs to act.

        Returns:
            Updated game state after action.
        """
        # Build context for player
        context: PokerDecisionContext = self._runner.build_context(game, player_id)
        available_actions: list[AvailableActions] = self._runner.get_available_actions(game, player_id)

        # Get player config
        player_config: PlayerConfig = self._runner.get_player_config(game, player_id)

        # Get action from provider
        self._logger.debug(
            "Requesting action",
            player_id=player_id,
            phase=game.current_phase.value,
        )

        response: ActionResponse[Action, Narration] = await self._action_provider.get_action(
            context,
            available_actions,
            player_config,
        )

        self._logger.debug(
            "Action received",
            player_id=player_id,
            action=response.action.action_type.value,
            amount=response.action.amount.value if response.action.amount else None,
        )

        # Apply action
        result: TurnResult[Game, Action, Narration, None] = self._runner.apply_action(
            game,
            player_id,
            response.action,
            response.narration,
        )

        self._total_actions += 1

        return result.state

    def _on_hand_completed(self, game: Game, hand_number: int) -> None:
        """Handle hand completion.

        Args:
            game: Current game state.
            hand_number: The hand number that completed.
        """
        self._logger.info(
            "Hand completed",
            hand_number=hand_number,
            players_remaining=len(game.get_active_players()),
        )

        # Persist if configured
        if self._persist_after_each_hand:
            self._persist()

        # Callback
        if self._on_hand_complete is not None:
            self._on_hand_complete(game, hand_number)

    def _determine_winner(self, game: Game) -> tuple[str, str] | None:
        """Determine the tournament winner.

        Args:
            game: Final game state.

        Returns:
            Tuple of (winner_id, winner_name) or None if no winner.
        """
        active_players = game.get_active_players()

        if len(active_players) == 1:
            winner: Player = active_players[0]
            # Get name from config if available
            if winner.id in self._runner._config.player_configs:
                name = self._runner._config.player_configs[winner.id].name
            else:
                name = str(winner.bot_id) if winner.bot_id else winner.id
            return (winner.id, name)

        if len(active_players) == 0:
            self._logger.warning("Tournament ended with no active players")
            return None

        # Multiple players remaining (shouldn't happen in normal play)
        self._logger.warning(
            "Tournament ended with multiple active players",
            count=len(active_players),
        )
        return None

    def _persist(self) -> None:
        """Persist current history to repository."""
        if self._repository is None:
            return

        history = self._runner.history
        if history is None:
            return

        try:
            self._repository.save(history)
            self._logger.debug("History persisted", game_id=history.game_id)
        except Exception as e:
            self._logger.error(
                "Failed to persist history",
                error=str(e),
            )

    def _persist_final(self) -> None:
        """Persist final history (always persists if repository available)."""
        if self._repository is None:
            return

        history = self._runner.history
        if history is None:
            return

        try:
            self._repository.save(history)
            self._logger.info("Final history persisted", game_id=history.game_id)
        except Exception as e:
            self._logger.error(
                "Failed to persist final history",
                error=str(e),
            )
