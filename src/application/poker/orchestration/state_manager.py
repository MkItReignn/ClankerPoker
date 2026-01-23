"""Poker game state manager."""

from __future__ import annotations

from dataclasses import replace as dataclass_replace
from datetime import UTC, datetime

from src.application.poker.context import PokerContextBuilder, PokerDecisionContext
from src.application.poker.orchestration.game_initializer import GameInitializer
from src.application.poker.records.models import GameRecord
from src.application.poker.records.recorder import Recorder
from src.application.poker.state_observers.details import (
    ActionAppliedDetails,
    BlindInfo,
    BlindsPostedDetails,
    GameCompletedDetails,
    GameStartedDetails,
    HandCompletedDetails,
    HandStartedDetails,
    RoundCompletedDetails,
    RoundStartedDetails,
)
from src.application.poker.state_observers.notifier import GameStateNotifier
from src.application.protocols.player import ActionResponse, PlayerConfig
from src.application.protocols.response import TurnResult
from src.config.poker.config import PokerGameConfig
from src.config.tournament.config import TournamentConfig
from src.domain.models.actions import Action
from src.domain.models.available_action import AvailableActions
from src.domain.models.deck import Deck
from src.domain.models.game import Game, GameIdentity, GamePhase, GameStatus, HandState
from src.domain.models.narration import Narration
from src.domain.models.player import Player
from src.domain.rules.action_applier import ActionApplier
from src.domain.rules.available_action_calculator import AvailableActionCalculator
from src.domain.rules.hand_engine import HandEngine
from src.domain.rules.position_manager import PositionManager
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

        # Initialize recorder and notifier
        self._recorder: Recorder = Recorder(player_configs=self._config.player_configs)
        self._notifier: GameStateNotifier = GameStateNotifier(observers=[self._recorder])

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

    async def apply_action(
        self,
        player_id: str,
        response: ActionResponse[Action, Narration],
    ) -> TurnResult[Action, Narration]:
        player: Player | None = self.game.players.get_by_id(player_id)
        if player is None:
            raise ValueError(f"Player {player_id} not found")

        new_state: Game = ActionApplier.apply_action(self.game, player_id, response.action)

        new_player: Player | None = new_state.players.get_by_id(player_id)
        if new_player is None:
            raise ValueError(f"Player {player_id} not found after action")

        details = ActionAppliedDetails(
            player_id=player_id,
            player_name=self._config.player_configs[player_id].name,
            action_type=response.action.action_type,
            amount=response.action.amount,
            narration=response.narration,
        )
        await self._notifier.on_action_applied(game=new_state, details=details)

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

    async def resolve_hand(self) -> None:
        """Award pots and record hand outcome.

        Precondition: is_hand_complete() (SHOWDOWN phase or only 1 player remains)
        Postcondition: Pots awarded, hand recorded in game record
        """
        if not self.is_hand_complete():
            raise ValueError(
                "Cannot resolve hand: hand is not complete "
                "(must be in SHOWDOWN or only 1 player remaining)"
            )

        # Complete current round (SHOWDOWN or early fold-out) for symmetric lifecycle
        await self._notifier.on_round_completed(
            game=self.game, details=RoundCompletedDetails()
        )

        new_state: Game = HandEngine.complete_hand(self.game)

        # Build hand completed details from resolved state
        hand_details = HandCompletedDetails(
            winners=[],  # Recorder derives from game state
            eliminated=[],
            showdown=None,
        )
        await self._notifier.on_hand_completed(game=new_state, details=hand_details)

        self._game = new_state

    async def mark_game_complete_if_over(self) -> bool:
        """Mark game as COMPLETED if only 1 active player remains.

        Precondition: Hand has been resolved
        Postcondition: status == COMPLETED if game is over

        Returns: True if game is now complete, False otherwise
        """
        active_players: list[Player] = self.game.get_active_players()
        if len(active_players) > 1:
            return False

        self._logger.info("Game complete - winner determined")

        winner = active_players[0]
        now: datetime = datetime.now(UTC)
        completed_identity: GameIdentity = dataclass_replace(
            self.game.identity,
            status=GameStatus.COMPLETED,
            completed_at=now,
            updated_at=now,
        )
        self.game.identity = completed_identity

        details = GameCompletedDetails(
            winner_id=winner.id,
            winner_name=self._config.player_configs[winner.id].name,
            total_hands=self.game.hand_state.hand_number,
        )
        await self._notifier.on_game_completed(game=self.game, details=details)

        return True

    async def start_next_round(self) -> GamePhase | None:
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

        # Complete the current round
        await self._notifier.on_round_completed(
            game=self.game, details=RoundCompletedDetails()
        )

        # Handle RIVER → SHOWDOWN (no cards to deal)
        if self.game.current_phase == GamePhase.RIVER:
            self._transition_to_showdown()
            round_details = RoundStartedDetails(
                phase=self.game.current_phase,
                new_cards=(),
            )
            await self._notifier.on_round_started(game=self.game, details=round_details)
            return self.game.current_phase

        # Normal phase advancement (PREFLOP → FLOP → TURN → RIVER)
        self._game = HandEngine.advance_betting_round(self.game)

        # Deal community cards for the new phase
        cards_before = len(self._game.community_cards)
        if (
            self._deck is not None
            and self._game.current_phase in (GamePhase.FLOP, GamePhase.TURN, GamePhase.RIVER)
            and cards_before < self._game.current_phase.card_count
        ):
            self._game, self._deck = HandEngine.deal_community_cards(self._game, self._deck)

        # Determine new cards dealt this round
        new_cards = tuple(self._game.community_cards[cards_before:])

        # Start the new round
        round_details = RoundStartedDetails(
            phase=self._game.current_phase,
            new_cards=new_cards,
        )
        await self._notifier.on_round_started(game=self._game, details=round_details)

        return self._game.current_phase

    async def start_new_hand(self) -> None:
        if self.game.status == GameStatus.COMPLETED:
            return  # Game is over, don't start new hand
        self._game = await self._init_new_hand(self.game)

    async def _init_new_hand(self, state: Game) -> Game:
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

        # Phase 1: Setup hand (deal hole cards, no blinds yet)
        pre_blind_state, self._deck = HandEngine.setup_hand(state, self._deck)

        # Notify hand started
        hand_details = HandStartedDetails(
            hand_number=pre_blind_state.hand_state.hand_number,
            button_seat=pre_blind_state.button_seat,
        )
        await self._notifier.on_hand_started(game=pre_blind_state, details=hand_details)

        # Notify round started (PRE_FLOP - no community cards yet)
        round_details = RoundStartedDetails(
            phase=pre_blind_state.current_phase,
            new_cards=(),
        )
        await self._notifier.on_round_started(game=pre_blind_state, details=round_details)

        # Phase 2: Post blinds
        post_blind_state = HandEngine.post_blinds(pre_blind_state)

        # Build blind details
        position_mapping = PositionManager.resolve_positions_for_hand(
            all_players=list(post_blind_state.players),
            previous_button_seat=post_blind_state.button_seat,
            advance_button=False,
        )
        sb_player = post_blind_state.players.get_by_seat(position_mapping.small_blind_seat)
        bb_player = post_blind_state.players.get_by_seat(position_mapping.big_blind_seat)

        blind_details = BlindsPostedDetails(
            small_blind=BlindInfo(
                player_id=sb_player.id if sb_player else "",
                player_name=self._config.player_configs[sb_player.id].name if sb_player else "",
                amount=sb_player.total_invested_this_hand if sb_player else post_blind_state.current_blind_level.small_blind,
            ),
            big_blind=BlindInfo(
                player_id=bb_player.id if bb_player else "",
                player_name=self._config.player_configs[bb_player.id].name if bb_player else "",
                amount=bb_player.total_invested_this_hand if bb_player else post_blind_state.current_blind_level.big_blind,
            ),
        )
        await self._notifier.on_blinds_posted(game=post_blind_state, details=blind_details)

        return post_blind_state

    async def initialize(self) -> None:
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
            details = GameStartedDetails(
                player_count=len(state.players),
                starting_chips=state.tournament_config.starting_chip_stack,
            )
            await self._notifier.on_game_started(game=state, details=details)

        self._game = await self._init_new_hand(state)
