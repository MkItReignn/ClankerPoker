"""Game state recorder for capturing game state snapshots."""

from __future__ import annotations

from datetime import datetime

from src.application.poker.records.models import (ActionRecord, GameMetadata,
                                                  GameRecord, PlayerConfig,
                                                  RoundRecord, TurnRecord)
from src.application.poker.state_observers.details import (
    ActionAppliedDetails,
    BlindInfo,
    BlindsPostedDetails,
    GameCompletedDetails,
    GameStartedDetails,
    HandCompletedDetails,
    HandStartedDetails,
    HoleCardsDealtDetails,
    PlayerToActDetails,
    RoundCompletedDetails,
    RoundStartedDetails,
)
from src.application.poker.records.recorder.hand_outcome_builder import \
    HandOutcomeBuilder
from src.application.poker.records.recorder.player_record_factory import \
    PlayerRecordFactory
from src.application.poker.records.recorder.record_logger import RecordLogger
from src.config.poker.config import PokerPlayerConfig
from src.domain.models.actions import ActionType
from src.domain.models.game import Game, GamePhase
from src.logger.factories import get_generic_logger


class Recorder:
    """Records game state snapshots at each level of the game hierarchy.

    Coordinates recording at game, hand, round, and turn levels.
    Delegates record building to specialized factories.
    """

    def __init__(self, player_configs: dict[str, PokerPlayerConfig]) -> None:
        self._player_configs = player_configs
        self._record: GameRecord | None = None
        self._logger = get_generic_logger(__name__.removeprefix("src."))
        self._record_logger = RecordLogger()
        self._player_record_factory = PlayerRecordFactory(player_configs)
        self._hand_outcome_builder = HandOutcomeBuilder(player_configs)

    @property
    def record(self) -> GameRecord | None:
        return self._record

    # =========================================================================
    # Game Lifecycle
    # =========================================================================

    async def on_game_started(self, game: Game, details: GameStartedDetails) -> None:
        metadata = GameMetadata.from_game(game)
        self._record = GameRecord(game.id, metadata)

        for player in game.players:
            poker_config = self._player_configs[player.id]
            player_config = PlayerConfig(
                personality=poker_config.personality,
                addon_prompt=poker_config.addon_prompt,
            )
            self._record.register_player(
                player_id=player.id,
                name=poker_config.name,
                seat=player.seat,
                model_id=poker_config.model_id,
                player_config=player_config,
            )

        self._record_logger.log_game_started(self._record)

    async def on_game_completed(self, game: Game, details: GameCompletedDetails) -> None:
        if self._record is not None:
            self._record.metadata.completed_at = game.identity.completed_at

    # =========================================================================
    # Hand Lifecycle
    # =========================================================================

    async def on_hand_started(self, game: Game, details: HandStartedDetails) -> None:
        if self._record is None:
            return

        hand_player_records = self._player_record_factory.create_hand_level_player_records(game)

        self._record.start_hand(
            hand_number=game.hand_state.hand_number,
            button_seat=game.button_seat,
            blinds=game.current_blind_level,
            player_records=hand_player_records,
        )

        if self._record.current_hand is not None:
            self._record_logger.log_hand_started(self._record.current_hand)

    async def on_hand_completed(self, game: Game, details: HandCompletedDetails) -> None:
        if self._record is None or self._record.current_hand is None:
            return

        outcome = self._hand_outcome_builder.build(game)
        self._record.complete_hand(outcome)
        self._record_logger.log_hand_completed_with_eliminations(self._record)

    # =========================================================================
    # Round Lifecycle
    # =========================================================================

    async def on_round_started(self, game: Game, details: RoundStartedDetails) -> None:
        if self._record is None or self._record.current_hand is None:
            return

        round_player_records = self._player_record_factory.create_round_level_player_records(game)
        community_cards = tuple(game.community_cards) if game.community_cards else ()

        round_record = self._record.current_hand.start_round(
            phase=game.current_phase,
            community_cards=community_cards,
            player_records=round_player_records,
        )

        if round_record.phase != GamePhase.PRE_FLOP:
            self._record_logger.log_round_advanced(self._record.current_hand, round_record)

    async def on_round_completed(self, game: Game, details: RoundCompletedDetails) -> None:
        if self._record is None or self._record.current_hand is None:
            return

        current_round = self._record.current_hand.current_round()
        if current_round is not None and not current_round.is_complete:
            current_round.complete()
            self._record_logger.log_betting_round_ended(self._record.current_hand, current_round)

    # =========================================================================
    # Action Recording
    # =========================================================================

    async def on_action_applied(self, game: Game, details: ActionAppliedDetails) -> None:
        if self._record is None or self._record.current_hand is None:
            return

        current_round: RoundRecord | None = self._record.current_hand.current_round()
        if current_round is None:
            return

        action_record = ActionRecord(
            player_id=details.player_id,
            player_name=details.player_name,
            phase=game.current_phase,
            action_type=details.action_type,
            amount=details.amount,
            timestamp=datetime.now(),
        )

        turn_record = TurnRecord(
            round_turn_number=len(current_round.turns) + 1,
            action=action_record,
            timestamp=datetime.now(),
            narration=details.narration,
        )

        current_round.add_turn(turn_record)
        self._record_logger.log_action_taken(turn_record, self._record.current_hand.hand_number)

    async def on_blinds_posted(self, game: Game, details: BlindsPostedDetails) -> None:
        if self._record is None or self._record.current_hand is None:
            return

        if game.current_phase != GamePhase.PRE_FLOP:
            return

        current_round = self._record.current_hand.current_round()
        if current_round is None:
            return

        self._record_blind_turn(
            current_round=current_round,
            blind_info=details.small_blind,
            action_type=ActionType.POST_SMALL_BLIND,
            phase=game.current_phase,
        )

        self._record_blind_turn(
            current_round=current_round,
            blind_info=details.big_blind,
            action_type=ActionType.POST_BIG_BLIND,
            phase=game.current_phase,
        )

    def _record_blind_turn(
        self,
        current_round: RoundRecord,
        blind_info: BlindInfo,
        action_type: ActionType,
        phase: GamePhase,
    ) -> None:
        action_record = ActionRecord(
            player_id=blind_info.player_id,
            player_name=blind_info.player_name,
            phase=phase,
            action_type=action_type,
            amount=blind_info.amount,
            timestamp=datetime.now(),
        )

        turn_record = TurnRecord(
            round_turn_number=len(current_round.turns) + 1,
            action=action_record,
            timestamp=datetime.now(),
        )

        current_round.add_turn(turn_record)

        if self._record is not None and self._record.current_hand is not None:
            self._record_logger.log_action_taken(
                turn_record, self._record.current_hand.hand_number
            )

    # =========================================================================
    # UI-Only Events (no-op for Recorder)
    # =========================================================================

    async def on_hole_cards_dealt(
        self, game: Game, details: HoleCardsDealtDetails
    ) -> None:
        del game, details

    async def on_player_to_act(
        self, game: Game, details: PlayerToActDetails
    ) -> None:
        del game, details
