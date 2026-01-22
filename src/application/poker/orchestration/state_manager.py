"""Poker game state manager."""

from __future__ import annotations

from dataclasses import replace as dataclass_replace
from datetime import UTC, datetime

from src.application.poker.context import PokerContextBuilder, PokerDecisionContext
from src.application.poker.records.models import GameMetadata, GameRecord
from src.application.poker.records.recorder import Recorder
from src.application.poker.orchestration.game_initializer import \
    GameInitializer
from src.application.protocols.player import ActionResponse, PlayerConfig
from src.application.protocols.response import TurnResult
from src.config.poker.config import PokerGameConfig
from src.config.tournament.config import TournamentConfig
from src.domain.models.actions import Action
from src.domain.models.available_action import AvailableActions
from src.domain.models.deck import Deck
from src.domain.models.game import (Game, GameIdentity, GamePhase, GameStatus,
                                    HandState)
from src.domain.models.narration import Narration
from src.domain.models.player import Player
from src.domain.rules.action_applier import ActionApplier
from src.domain.rules.available_action_calculator import \
    AvailableActionCalculator
from src.domain.rules.hand_engine import HandEngine
from src.domain.utils.seed_sequence import SeedSequence
from src.logger.factories import get_generic_logger


class PokerStateManager:
    def __init__(
        self,
        config: PokerGameConfig,
        tournament_config: TournamentConfig,
        game_id: str,
        seed: int,
        record: GameRecord | None = None,
    ) -> None:
        self._logger = get_generic_logger(__name__.removeprefix("src."))

        self._config: PokerGameConfig = config
        self._tournament_config: TournamentConfig = tournament_config
        self._game_id: str = game_id
        self._seed: int = seed

        # Internal game state (created by initialize_game)
        self._game: Game | None = None
        self._deck: Deck | None = None

        player_names = self.player_names
        self._context_builder: PokerContextBuilder = PokerContextBuilder(player_names=player_names)

        # Initialize recorder with player configs dict
        self._recorder: Recorder = Recorder(
            player_configs=self._config.player_configs
        )

        # If record was provided, set it on the recorder
        if record is not None:
            self._recorder._record = record

    @property
    def game(self) -> Game:
        if self._game is None:
            raise RuntimeError("Game not initialized. Call initialize() first.")
        return self._game

    @property
    def record(self) -> GameRecord | None:
        """Get the current game record."""
        return self._recorder.record

    @property
    def player_names(self) -> dict[str, str]:
        """Get the player names mapping."""
        return {pid: cfg.name for pid, cfg in self._config.player_configs.items()}

    def get_player_to_act_id(self) -> str | None:
        """Get the ID of the player who needs to act."""
        return self.game.get_player_to_act_id()

    def get_player_config(self, player_id: str) -> PlayerConfig:
        if player_id not in self._config.player_configs:
            raise ValueError(
                f"Player configuration not found for player_id '{player_id}'. "
                f"Please add configuration for this player in config/poker/poker.json. "
                f"Available configured players: {list(self._config.player_configs.keys())}"
            )

        return self._config.player_configs[player_id].to_player_config()

    def build_context(self, player_id: str) -> PokerDecisionContext:
        return self._context_builder.build_context(
            state=self.game,
            player_id=player_id,
            record=self._recorder.record,
        )

    def get_available_actions(self, player_id: str) -> list[AvailableActions]:
        return AvailableActionCalculator.calculate_available_actions(self.game, player_id)

    def apply_action(
        self,
        player_id: str,
        response: ActionResponse[Action, Narration],
    ) -> TurnResult[Action, Narration]:
        """Apply an action to the game state."""
        # Capture state BEFORE action
        player: Player | None = self.game.players.get_by_id(player_id)
        if player is None:
            raise ValueError(f"Player {player_id} not found")

        # Apply the action
        new_state: Game = ActionApplier.apply_action(self.game, player_id, response.action)

        # Verify player exists after action
        new_player: Player | None = new_state.players.get_by_id(player_id)
        if new_player is None:
            raise ValueError(f"Player {player_id} not found after action")

        self._recorder.record_action(
            state=new_state,
            player_id=player_id,
            response=response,
        )

        self._game = new_state

        return TurnResult(
            player_id=player_id,
            response=response,
        )

    def is_game_complete(self) -> bool:
        return self.game.status == GameStatus.COMPLETED

    def is_hand_complete(self) -> bool:
        return self.game.is_hand_complete()

    def is_round_complete(self) -> bool:
        return self.game.is_round_complete()

    def _transition_to_showdown(self) -> None:
        """Transition from RIVER to SHOWDOWN phase (internal).

        Called by start_next_round() when current phase is RIVER.
        """
        if self.game.current_phase != GamePhase.RIVER:
            raise ValueError(
                f"Cannot transition to showdown: must be in RIVER phase, "
                f"currently in {self.game.current_phase}"
            )

        if not self.is_round_complete():
            raise ValueError("Cannot transition to showdown: RIVER betting not complete")

        players_in_hand = list(self.game.players_in_hand())
        if len(players_in_hand) <= 1:
            raise ValueError("Cannot transition to showdown: need 2+ players for showdown")

        showdown_hand_state = HandState(
            hand_number=self.game.hand_state.hand_number,
            current_phase=GamePhase.SHOWDOWN,
            community_cards=self.game.hand_state.community_cards,
            is_initial_hand_setup=self.game.hand_state.is_initial_hand_setup,
        )
        self.game.hand_state = showdown_hand_state

    def resolve_hand(self) -> None:
        """Award pots and record hand outcome.

        Precondition: is_hand_complete() (SHOWDOWN phase or only 1 player remains)
        Postcondition: Pots awarded, hand recorded in game record
        """
        if not self.is_hand_complete():
            raise ValueError(
                "Cannot resolve hand: hand is not complete "
                "(must be in SHOWDOWN or only 1 player remaining)"
            )

        new_state: Game = HandEngine.complete_hand(self.game)
        self._recorder.record_hand_complete(new_state)
        self._game = new_state

    def mark_game_complete_if_over(self) -> bool:
        """Mark game as COMPLETED if only 1 active player remains.

        Precondition: Hand has been resolved
        Postcondition: status == COMPLETED if game is over

        Returns: True if game is now complete, False otherwise
        """
        active_players: list[Player] = self.game.get_active_players()
        if len(active_players) > 1:
            return False

        self._logger.info("Game complete - winner determined")

        now: datetime = datetime.now(UTC)
        completed_identity: GameIdentity = dataclass_replace(
            self.game.identity,
            status=GameStatus.COMPLETED,
            completed_at=now,
            updated_at=now,
        )
        self.game.identity = completed_identity
        self._recorder.record_game_complete(now)

        return True

    def start_next_round(self) -> GamePhase | None:
        """Transition to the next phase.

        Handles all phase transitions:
        - PREFLOP → FLOP (deal 3 cards)
        - FLOP → TURN (deal 1 card)
        - TURN → RIVER (deal 1 card)
        - RIVER → SHOWDOWN (no cards)

        Returns:
            The new game phase after transitioning, or None if hand is over.
        """
        # No-op if hand is already complete (e.g., everyone folded)
        if len(list(self.game.players_in_hand())) <= 1:
            return None

        if not self.is_round_complete():
            raise ValueError("Cannot transition to next round: round is not complete")

        # Complete the current round in game record
        self._recorder.record_round_complete()

        # Handle RIVER → SHOWDOWN (no cards to deal)
        if self.game.current_phase == GamePhase.RIVER:
            self._transition_to_showdown()
            self._recorder.record_round_start(self.game)
            return GamePhase.SHOWDOWN

        # Normal phase advancement (PREFLOP → FLOP → TURN → RIVER)
        self._game = HandEngine.advance_betting_round(self.game)

        # Deal community cards for the new phase
        if (
            self._deck is not None
            and self._game.current_phase in (GamePhase.FLOP, GamePhase.TURN, GamePhase.RIVER)
            and len(self._game.community_cards) < self._game.current_phase.card_count
        ):
            self._game, self._deck = HandEngine.deal_community_cards(self._game, self._deck)

        # Start the new round in game record
        self._recorder.record_round_start(self._game)

        return self._game.current_phase

    def start_new_hand(self) -> None:
        if self.game.status == GameStatus.COMPLETED:
            return  # Game is over, don't start new hand
        self._game = self._init_new_hand(self.game)

    def _init_new_hand(self, state: Game) -> Game:
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

        # Phase 1: Setup hand (deal cards, no blinds yet)
        pre_blind_state, self._deck = HandEngine.setup_hand(state, self._deck)

        # Record pre-blind state for hand and round
        self._recorder.record_hand_start(pre_blind_state)
        self._recorder.record_round_start(pre_blind_state)

        # Phase 2: Post blinds
        post_blind_state = HandEngine.post_blinds(pre_blind_state)

        # Record blind postings
        self._recorder.record_blind_postings(state=post_blind_state)

        return post_blind_state

    def initialize(self) -> None:
        """Initialize the game state.

        Creates the game with button assigned, initializes game record, and deals first hand.
        """
        player_configs = list(self._config.player_configs.values())

        state = GameInitializer.create_tournament(
            player_configs=player_configs,
            tournament_config=self._tournament_config,
            seed=self._seed,
            game_id=self._game_id,
        )

        if self._recorder.record is None:
            metadata = GameMetadata(
                seed=state.identity.seed,
                buy_in_amount=state.tournament_config.buy_in_amount,
                starting_chip_stack=state.tournament_config.starting_chip_stack,
                blind_schedule=state.tournament_config.blind_schedule,
                payout_structure=state.tournament_config.payout_structure,
                started_at=state.identity.started_at,
            )
            self._recorder.record_game_start(state, metadata)

        self._game = self._init_new_hand(state)
