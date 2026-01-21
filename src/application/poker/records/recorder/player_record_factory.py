"""Factory for creating player record snapshots at different game levels."""

from __future__ import annotations

from src.application.poker.records.models import (HandLevelPlayerRecord,
                                                  RoundLevelPlayerRecord,
                                                  TurnLevelPlayerRecord)
from src.config.poker.config import PokerPlayerConfig
from src.domain.models.chips import ChipAmount
from src.domain.models.game import Game
from src.domain.models.llm_model import LlmModel
from src.domain.models.player import HandParticipationStatus, Player
from src.domain.models.position import PositionName, TablePositionMapping
from src.domain.rules.position_manager import PositionManager


class PlayerRecordFactory:
    """Creates player record snapshots at hand, round, and turn levels."""

    def __init__(self, player_configs: dict[str, PokerPlayerConfig]) -> None:
        self._player_configs = player_configs

    def _get_player_name(self, player_id: str) -> str:
        if player_id not in self._player_configs:
            raise KeyError(f"Player ID '{player_id}' not found in player_configs")
        return self._player_configs[player_id].name

    def _get_player_model_id(self, player_id: str) -> LlmModel:
        if player_id not in self._player_configs:
            raise KeyError(f"Player ID '{player_id}' not found in player_configs")
        return self._player_configs[player_id].model_id

    def create_hand_level_player_records(self, state: Game) -> dict[str, HandLevelPlayerRecord]:
        """Create hand-level player records for all active players."""
        position_mapping: TablePositionMapping = PositionManager.resolve_positions_for_hand(
            all_players=list(state.players),
            previous_button_seat=state.button_seat,
            advance_button=False,
        )

        records: dict[str, HandLevelPlayerRecord] = {}
        for player in state.players:
            if player.participation_status != HandParticipationStatus.ELIMINATED:
                position_name: PositionName | None = position_mapping.get_position_for_seat(
                    player.seat
                )
                records[player.id] = HandLevelPlayerRecord(
                    player_id=player.id,
                    player_name=self._get_player_name(player.id),
                    seat=player.seat,
                    chips=player.remaining_chips,
                    model_id=self._get_player_model_id(player.id),
                    hole_cards=player.hole_cards,
                    position=position_name,
                    starting_chips=player.remaining_chips,
                )
        return records

    def create_round_level_player_records(self, state: Game) -> dict[str, RoundLevelPlayerRecord]:
        """Create round-level player records for all players."""
        records: dict[str, RoundLevelPlayerRecord] = {}

        for player in state.players:
            participation_status = player.participation_status
            total_invested = player.total_invested_this_hand

            records[player.id] = RoundLevelPlayerRecord(
                player_id=player.id,
                player_name=self._get_player_name(player.id),
                seat=player.seat,
                chips=player.remaining_chips,
                model_id=self._get_player_model_id(player.id),
                chips_at_round_start=player.remaining_chips,
                total_invested_in_hand_at_round_start=total_invested,
                participation_status=participation_status,
                is_all_in=player.is_all_in(),
            )
        return records

    def create_turn_level_player_record(
        self, player: Player, invested_before: int
    ) -> TurnLevelPlayerRecord:
        """Create turn-level player record capturing state before action."""
        return TurnLevelPlayerRecord(
            player_id=player.id,
            player_name=self._get_player_name(player.id),
            seat=player.seat,
            chips=player.remaining_chips,
            model_id=self._get_player_model_id(player.id),
            total_invested_before_action=ChipAmount(invested_before),
            can_raise=player.can_raise,
        )
