"""Poker-specific game runner implementation."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, UTC

from src.application.poker.context import (PokerContextBuilder,
                                           PokerDecisionContext)
from src.application.poker.history.models import GameHistory, GameMetadata
from src.application.poker.history.recorder import HistoryRecorder
from src.application.protocols.player import PlayerConfig
from src.application.use_cases.game_runner import GameRunner, TurnResult
from src.config.poker.config import PokerGameConfig
from src.config.poker.config_loader import PokerGameConfigLoader
from src.domain.models.actions import Action
from src.domain.models.available_action import AvailableActions
from src.domain.models.deck import Deck
from src.domain.models.game import Game, GamePhase, GameStatus
from src.domain.models.narration import Narration
from src.domain.models.player import Player
from src.domain.rules.action_applier import ActionApplier
from src.domain.rules.available_action_calculator import \
    AvailableActionCalculator
from src.domain.rules.game_orchestrator import GameOrchestrator
from src.domain.rules.hand_engine import HandEngine
from src.domain.utils.seed_sequence import SeedSequence
from src.logger.factories import get_generic_logger


class PokerGameRunner(
    GameRunner[
        Game,
        PokerDecisionContext,
        list[AvailableActions],
        Action,
        Narration,
        None,
    ]
):
    """Poker-specific game runner.

    Orchestrates poker games by coordinating:
    - Hand initialization and completion
    - Betting round management
    - Action application
    - Game history tracking (via HistoryRecorder)
    """

    def __init__(
        self,
        config: PokerGameConfig | None = None,
        history: GameHistory | None = None,
    ) -> None:
        """Initialize the poker game runner.

        Args:
            config: Optional game configuration.
                If None, loads configuration from config/poker/poker.json using PokerGameConfigLoader.
            history: Optional pre-existing game history.
        """
        super().__init__()
        # Override parent logger with poker-specific logger
        self._logger = get_generic_logger(__name__.removeprefix("src."))

        if config is None:
            loader: PokerGameConfigLoader = PokerGameConfigLoader()
            self._config: PokerGameConfig = loader.load()
        else:
            self._config = config

        self._deck: Deck | None = None
        player_names = self.player_names
        self._context_builder: PokerContextBuilder = PokerContextBuilder(player_names=player_names)

        # Initialize history recorder with player names dict
        self._recorder = HistoryRecorder(player_names=player_names)

        # If history was provided, set it on the recorder
        if history is not None:
            self._recorder._history = history

    @property
    def history(self) -> GameHistory | None:
        """Get the current game history."""
        return self._recorder.history

    @property
    def player_names(self) -> dict[str, str]:
        """Get the player names mapping."""
        return {pid: cfg.name for pid, cfg in self._config.player_configs.items()}

    def get_current_player_id(self, state: Game) -> str | None:
        """Get the ID of the player who needs to act."""
        return state.get_current_player_id()

    def get_player_config(self, state: Game, player_id: str) -> PlayerConfig:
        if player_id not in self._config.player_configs:
            raise ValueError(
                f"Player configuration not found for player_id '{player_id}'. "
                f"Please add configuration for this player in config/poker/poker.json. "
                f"Available configured players: {list(self._config.player_configs.keys())}"
            )

        return self._config.player_configs[player_id].to_player_config()

    def build_context(
        self,
        state: Game,
        player_id: str,
    ) -> PokerDecisionContext:
        """Build decision context for a player."""
        return self._context_builder.build_context(
            state=state,
            player_id=player_id,
            history=self._recorder.history,
        )

    def get_available_actions(
        self,
        state: Game,
        player_id: str,
    ) -> list[AvailableActions]:
        """Get available actions for a player."""
        return AvailableActionCalculator.calculate_available_actions(state, player_id)

    def apply_action(
        self,
        state: Game,
        player_id: str,
        action: Action,
        narration: Narration | None = None,
    ) -> TurnResult[Game, Action, Narration, None]:
        """Apply an action to the game state."""
        # Capture state BEFORE action
        player: Player | None = state.players.get_by_id(player_id)
        if player is None:
            raise ValueError(f"Player {player_id} not found")

        # Apply the action
        new_state: Game = ActionApplier.apply_action(state, player_id, action)

        # Verify player exists after action
        new_player: Player | None = new_state.players.get_by_id(player_id)
        if new_player is None:
            raise ValueError(f"Player {player_id} not found after action")

        # Record in history
        self._recorder.record_action(
            state_before=state,
            state_after=new_state,
            player_id=player_id,
            action=action,
        )

        return TurnResult(
            state=new_state,
            player_id=player_id,
            action=action,
            narration=narration,
        )

    def is_game_over(self, state: Game) -> bool:
        """Check if the game is over."""
        return state.status == GameStatus.COMPLETED

    def advance_game_phase(self, state: Game) -> Game:
        """Advance the game to the next phase if needed."""
        if state.is_hand_complete():
            return self._complete_hand(state)

        if state.is_round_complete():
            # RIVER complete with 2+ players → go to showdown
            if state.current_phase == GamePhase.RIVER:
                return self._complete_hand(state)
            return self._advance_round(state)

        return state

    def _complete_hand(self, state: Game) -> Game:
        """Complete the current hand and start a new one if needed."""
        from dataclasses import replace as dataclass_replace

        from src.domain.models.game import GameIdentity, GameStatus, HandState

        # Transition to SHOWDOWN if needed (when RIVER completes with 2+ players)
        if state.current_phase != GamePhase.SHOWDOWN:
            players_in_hand: list[Player] = list(state.players_in_hand())
            if len(players_in_hand) > 1:
                # Update phase to SHOWDOWN
                showdown_hand_state = HandState(
                    hand_number=state.hand_state.hand_number,
                    current_phase=GamePhase.SHOWDOWN,
                    community_cards=state.hand_state.community_cards,
                    is_initial_hand_setup=state.hand_state.is_initial_hand_setup,
                )
                state.hand_state = showdown_hand_state

        # Complete the hand
        new_state: Game = HandEngine.complete_hand(state)

        # Record hand outcome in history
        self._recorder.record_hand_complete(new_state)

        # Check if game is over (only one player left or tournament complete)
        active_players: list[Player] = new_state.get_active_players()
        if len(active_players) <= 1:
            self._logger.info("Game complete - winner determined")
            # Set status to COMPLETED
            now: datetime = datetime.now(UTC)
            completed_identity: GameIdentity = dataclass_replace(
                new_state.identity,
                status=GameStatus.COMPLETED,
                completed_at=now,
                updated_at=now,
            )
            new_state.identity = completed_identity

            # Record completion time in history
            self._recorder.complete_game(now)

            return new_state

        # Start new hand
        return self._start_new_hand(new_state)

    def _advance_round(self, state: Game) -> Game:
        """Advance to the next betting round."""
        # Complete the current round in history
        self._recorder.record_round_complete()

        # Advance the betting round FIRST (changes phase)
        state = HandEngine.advance_betting_round(state)

        # THEN deal community cards if needed for the new phase
        if (
            self._deck is not None
            and state.current_phase in (GamePhase.FLOP, GamePhase.TURN, GamePhase.RIVER)
            and len(state.community_cards) < state.current_phase.card_count
        ):
            state, self._deck = HandEngine.deal_community_cards(state, self._deck)

        # Start the new round in history
        self._recorder.record_round_start(state)

        return state

    def _start_new_hand(self, state: Game) -> Game:
        """Start a new hand."""
        # Determine next hand number
        if state.hand_state.is_initial_hand_setup:
            next_hand_number = 1
        else:
            next_hand_number = state.hand_state.hand_number + 1

        # Create seed sequence and get shuffle seed for this hand
        seed_sequence = SeedSequence(base_seed=state.identity.seed)
        shuffle_seed = seed_sequence.get_shuffle_seed_for_hand(next_hand_number)

        # Create fresh deck with deterministic seed
        self._deck = Deck.create_shuffled(seed=shuffle_seed)

        # Initialize hand
        new_state, self._deck = HandEngine.initialize_hand(state, self._deck)

        # Record hand start and first round in history
        self._recorder.record_hand_start(new_state)
        self._recorder.record_round_start(new_state)

        return new_state

    def initialize_game(self, state: Game) -> Game:
        """Initialize a game for running.

        Sets up the deck, history, determines initial button, and starts the first hand.
        Transitions the game status from WAITING to IN_PROGRESS.

        Args:
            state: The initial game state.

        Returns:
            The initialized game state ready for play.
        """

        from src.domain.models.game import GameStatus

        # Transition status from WAITING to IN_PROGRESS
        if state.identity.status == GameStatus.WAITING:
            now = datetime.now(UTC)
            new_identity = replace(
                state.identity,
                status=GameStatus.IN_PROGRESS,
                started_at=now,
                updated_at=now,
            )
            state = Game(
                identity=new_identity,
                tournament_config=state.tournament_config,
                hand_state=state.hand_state,
                pot_state=state.pot_state,
                betting_state=state.betting_state,
                button_seat=state.button_seat,
                blind_state=state.blind_state,
                players=state.players,
                results=state.results,
            )

        # Initialize button using high card draw (if initial hand setup)
        if state.hand_state.is_initial_hand_setup:
            state = GameOrchestrator.initialize_game(state)

        # Initialize history if needed
        if self._recorder.history is None:
            metadata: GameMetadata = GameMetadata(
                seed=state.identity.seed,
                buy_in_amount=state.tournament_config.buy_in_amount,
                starting_chip_stack=state.tournament_config.starting_chip_stack,
                blind_schedule=state.tournament_config.blind_schedule,
                payout_structure=state.tournament_config.payout_structure,
                started_at=state.identity.started_at,
            )
            self._recorder.initialize_history(state, metadata)

        # Start first hand
        return self._start_new_hand(state)
