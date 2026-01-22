"""Game state recorder for capturing game state snapshots."""

from __future__ import annotations

from datetime import datetime

from src.application.poker.records.models import (ActionRecord, GameMetadata,
                                                  GameRecord, PlayerConfig,
                                                  RoundRecord, TurnRecord)
from src.application.poker.records.recorder.hand_outcome_builder import \
    HandOutcomeBuilder
from src.application.poker.records.recorder.player_record_factory import \
    PlayerRecordFactory
from src.application.poker.records.recorder.record_logger import RecordLogger
from src.application.protocols.player import ActionResponse
from src.config.poker.config import PokerPlayerConfig
from src.domain.models.actions import Action, ActionType
from src.domain.models.chips import ChipAmount
from src.domain.models.game import Game, GamePhase
from src.domain.models.narration import Narration
from src.domain.models.player import Player
from src.domain.rules.betting_calculator import BettingCalculator
from src.domain.rules.position_manager import PositionManager
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

    def record_game_start(self, state: Game, metadata: GameMetadata) -> None:
        """Record game start with metadata and register all players."""
        self._record = GameRecord(state.id, metadata)

        for player in state.players:
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

    def record_game_complete(self, completed_at: datetime) -> None:
        """Record game completion."""
        if self._record is not None:
            self._record.metadata.completed_at = completed_at

    # =========================================================================
    # Hand Lifecycle
    # =========================================================================

    def record_hand_start(self, state: Game) -> None:
        """Record the start of a new hand."""
        if self._record is None:
            return

        hand_player_records = self._player_record_factory.create_hand_level_player_records(state)

        self._record.start_hand(
            hand_number=state.hand_state.hand_number,
            button_seat=state.button_seat,
            blinds=state.current_blind_level,
            player_records=hand_player_records,
        )

        if self._record.current_hand is not None:
            self._record_logger.log_hand_started(self._record.current_hand)

    def record_hand_complete(self, state: Game) -> None:
        """Record the completion of a hand."""
        if self._record is None or self._record.current_hand is None:
            return

        outcome = self._hand_outcome_builder.build(state)
        self._record.complete_hand(outcome)
        self._record_logger.log_hand_completed_with_eliminations(self._record)

    # =========================================================================
    # Round Lifecycle
    # =========================================================================

    def record_round_start(self, state: Game) -> None:
        """Record the start of a betting round."""
        if self._record is None or self._record.current_hand is None:
            return

        round_player_records = self._player_record_factory.create_round_level_player_records(state)
        community_cards = tuple(state.community_cards) if state.community_cards else ()

        round_record = self._record.current_hand.start_round(
            phase=state.current_phase,
            community_cards=community_cards,
            player_records=round_player_records,
        )

        if round_record.phase != GamePhase.PRE_FLOP:
            self._record_logger.log_round_advanced(self._record.current_hand, round_record)

    def record_round_complete(self) -> None:
        """Record the completion of a betting round."""
        if self._record is None or self._record.current_hand is None:
            return

        current_round = self._record.current_hand.current_round()
        if current_round is not None and not current_round.is_complete:
            current_round.complete()
            self._record_logger.log_betting_round_ended(self._record.current_hand, current_round)

    # =========================================================================
    # Action Recording
    # =========================================================================

    def record_action(
        self,
        state_before: Game,
        state_after: Game,
        player_id: str,
        response: ActionResponse[Action, Narration],
    ) -> None:
        """Record an action taken by a player."""
        if self._record is None or self._record.current_hand is None:
            return

        current_round: RoundRecord | None = self._record.current_hand.current_round()
        if current_round is None:
            return

        player = state_before.players.get_by_id(player_id)
        if player is None:
            return

        invested_before = self._calculate_invested_before(player)
        turn_player_record = self._player_record_factory.create_turn_level_player_record(
            player, invested_before
        )

        action = response.action
        action_record = ActionRecord(
            player_id=player_id,
            player_name=self._player_configs[player_id].name,
            phase=state_before.current_phase,
            action_type=action.action_type,
            amount=action.amount,
            timestamp=datetime.now(),
        )

        turn_record = TurnRecord(
            round_turn_number=len(current_round.turns) + 1,
            player_record=turn_player_record,
            action=action_record,
            timestamp=datetime.now(),
            pot_before=state_before.pot,
            pot_after=state_after.pot,
            current_bet_before=self._get_bet_to_match(state_before),
            current_bet_after=self._get_bet_to_match(state_after),
            narration=response.narration,
        )

        current_round.add_turn(turn_record)
        self._record_logger.log_action_taken(turn_record, self._record.current_hand.hand_number)

    def record_blind_postings(self, state_before: Game, state_after: Game) -> None:
        if self._record is None or self._record.current_hand is None:
            return

        if state_after.current_phase != GamePhase.PRE_FLOP:
            return

        current_round = self._record.current_hand.current_round()
        if current_round is None:
            return

        position_mapping = PositionManager.resolve_positions_for_hand(
            all_players=list(state_after.players),
            previous_button_seat=state_after.button_seat,
            advance_button=False,
        )

        sb_player = state_after.players.get_by_seat(position_mapping.small_blind_seat)
        bb_player = state_after.players.get_by_seat(position_mapping.big_blind_seat)

        sb_amount = sb_player.total_invested_this_hand if sb_player else ChipAmount(0)
        bb_amount = bb_player.total_invested_this_hand if bb_player else ChipAmount(0)

        if sb_player is not None:
            self._record_blind_turn(
                current_round=current_round,
                player=sb_player,
                action_type=ActionType.POST_SMALL_BLIND,
                amount=sb_amount,
                phase=state_after.current_phase,
                pot_after=sb_amount,
            )

        if bb_player is not None:
            self._record_blind_turn(
                current_round=current_round,
                player=bb_player,
                action_type=ActionType.POST_BIG_BLIND,
                amount=bb_amount,
                phase=state_after.current_phase,
                pot_after=sb_amount + bb_amount,
            )

    def _record_blind_turn(
        self,
        current_round: RoundRecord,
        player: Player,
        action_type: ActionType,
        amount: ChipAmount,
        phase: GamePhase,
        pot_after: ChipAmount,
    ) -> None:
        turn_player_record = self._player_record_factory.create_turn_level_player_record(
            player, invested_before=0
        )

        action_record = ActionRecord(
            player_id=player.id,
            player_name=self._player_configs[player.id].name,
            phase=phase,
            action_type=action_type,
            amount=amount,
            timestamp=datetime.now(),
        )

        pot_before = ChipAmount(pot_after.value - amount.value)

        turn_record = TurnRecord(
            round_turn_number=len(current_round.turns) + 1,
            player_record=turn_player_record,
            action=action_record,
            timestamp=datetime.now(),
            pot_before=pot_before,
            pot_after=pot_after,
            current_bet_before=ChipAmount(0) if action_type == ActionType.POST_SMALL_BLIND else amount,
            current_bet_after=amount,
            narration=None,
        )

        current_round.add_turn(turn_record)

        if self._record is not None and self._record.current_hand is not None:
            self._record_logger.log_action_taken(
                turn_record, self._record.current_hand.hand_number
            )

    @staticmethod
    def _calculate_invested_before(player: Player) -> int:
        if player.stack_at_hand_start is None:
            return 0
        return player.stack_at_hand_start.value - player.remaining_chips.value

    @staticmethod
    def _get_bet_to_match(state: Game) -> ChipAmount:
        return BettingCalculator.get_max_invested_this_hand(state.players_in_hand())
