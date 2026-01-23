"""Poker game state manager."""

from __future__ import annotations

from dataclasses import replace as dataclass_replace
from datetime import UTC, datetime

from src.application.poker.context import PokerContextBuilder, PokerDecisionContext
from src.application.poker.orchestration.game_initializer import GameInitializer
from src.application.poker.records.models import GameRecord
from src.application.poker.records.recorder import Recorder
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
        return self._recorder.record

    @property
    def player_names(self) -> dict[str, str]:
        return {pid: cfg.name for pid, cfg in self._config.player_configs.items()}

    def get_player_to_act_id(self) -> str | None:
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

        await self._notifier.on_action_applied(
            game=new_state, player_id=player_id, response=response
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
        if not self.is_hand_complete():
            raise ValueError(
                "Cannot resolve hand: hand is not complete "
                "(must be in SHOWDOWN or only 1 player remaining)"
            )

        await self._notifier.on_round_completed(game=self.game)

        new_state: Game = HandEngine.complete_hand(self.game)

        await self._notifier.on_hand_completed(game=new_state)

        self._game = new_state

    async def mark_game_complete_if_over(self) -> bool:
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

        await self._notifier.on_game_completed(game=self.game)

        return True

    async def start_next_round(self) -> GamePhase | None:
        if len(list(self.game.players_in_hand())) <= 1:
            return None

        if not self.is_round_complete():
            raise ValueError("Cannot transition to next round: round is not complete")

        await self._notifier.on_round_completed(game=self.game)

        if self.game.current_phase == GamePhase.RIVER:
            self._transition_to_showdown()
            await self._notifier.on_round_started(game=self.game)
            return self.game.current_phase

        self._game = HandEngine.advance_betting_round(self.game)

        cards_before = len(self._game.community_cards)
        if (
            self._deck is not None
            and self._game.current_phase in (GamePhase.FLOP, GamePhase.TURN, GamePhase.RIVER)
            and cards_before < self._game.current_phase.card_count
        ):
            self._game, self._deck = HandEngine.deal_community_cards(self._game, self._deck)

        await self._notifier.on_round_started(game=self._game)

        return self._game.current_phase

    async def start_new_hand(self) -> None:
        if self.game.status == GameStatus.COMPLETED:
            return
        self._game = await self._init_new_hand(self.game)

    async def _init_new_hand(self, state: Game) -> Game:
        if state.hand_state.is_initial_hand_setup:
            next_hand_number = 1
        else:
            next_hand_number = state.hand_state.hand_number + 1

        seed_sequence = SeedSequence(base_seed=state.identity.seed)
        shuffle_seed = seed_sequence.get_shuffle_seed_for_hand(next_hand_number)

        self._deck = Deck.create_shuffled(seed=shuffle_seed)

        pre_blind_state, self._deck = HandEngine.setup_hand(state, self._deck)

        await self._notifier.on_hand_started(game=pre_blind_state)
        await self._notifier.on_hole_cards_dealt(game=pre_blind_state)
        await self._notifier.on_round_started(game=pre_blind_state)

        post_blind_state = HandEngine.post_blinds(pre_blind_state)

        await self._notifier.on_blinds_posted(game=post_blind_state)

        return post_blind_state

    async def initialize(self) -> None:
        player_configs = list(self._config.player_configs.values())

        state = GameInitializer.create_tournament(
            player_configs=player_configs,
            tournament_config=self._tournament_config,
            seed=self._seed,
            game_id=self._game_id,
        )

        if self._recorder.record is None:
            await self._notifier.on_game_started(game=state)

        self._game = await self._init_new_hand(state)
