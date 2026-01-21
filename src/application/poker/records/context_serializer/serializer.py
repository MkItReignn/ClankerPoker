from __future__ import annotations

from src.application.poker.records.context_serializer.dtos import (
    CurrentHandActionsDto, PreviousHandsDto)
from src.application.poker.records.models import GameRecord, HandRecord


class RecordToLlmContextSerializer:
    """Serializes game records into text for LLM prompt context."""

    @staticmethod
    def serialize_recent_records(
        record: GameRecord,
        viewer_id: str | None = None,
        max_hands: int = 5,
    ) -> str:
        dto = PreviousHandsDto.from_game_record(record, viewer_id, max_hands)
        return dto.serialize()

    @staticmethod
    def serialize_current_hand_actions(
        hand: HandRecord,
        current_phase: str,
    ) -> str:
        dto = CurrentHandActionsDto.from_hand_record(hand, current_phase)
        return dto.serialize()
