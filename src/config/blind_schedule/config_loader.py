"""Blind schedule configuration loader.

Loads a single blind schedule configuration from a schedule file (e.g., schedules/standard.json).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, final, override

import structlog

from src.config.base.config_loader import BaseConfigLoader
from src.config.blind_schedule.config import BlindSchedule, BlindScheduleEntry
from src.config.utils.type_extractors import ConfigTypeExtractor
from src.domain.models.blinds import BlindLevel
from src.domain.models.chips import ChipAmount
from src.logger.factories import get_generic_logger


@final
class BlindScheduleLoader(BaseConfigLoader[BlindSchedule]):
    """Loads a single blind schedule configuration from a schedule file.

    Loads and validates a blind schedule from a single schedule file
    (e.g., schedules/standard.json, schedules/turbo.json).
    """

    def __init__(
        self,
        config_path: Path,
        logger: structlog.BoundLogger | None = None,
        *,
        json_loader: Any = None,
    ) -> None:
        """Initialize blind schedule config loader.

        Args:
            config_path: Path to schedule file (e.g., schedules/standard.json).
            logger: Optional logger. Defaults to creating one.
            json_loader: Optional JSON loader (for testing).
        """
        resolved_logger = logger or get_generic_logger(__name__.removeprefix("src."))
        super().__init__(
            config_path=config_path,
            logger=resolved_logger,
            json_loader=json_loader,
        )

    @override
    def _load_config(self) -> BlindSchedule:
        """Load blind schedule configuration from a schedule file.

        Returns:
            BlindSchedule object.

        Raises:
            FileNotFoundError: If schedule file does not exist.
            ValueError: If config cannot be parsed or required fields are missing.
        """
        payload = self._json_loader.load()
        extractor = ConfigTypeExtractor(logger=self._logger)

        entries_raw = payload.get("entries")
        if entries_raw is None:
            raise ValueError("entries is required in schedule file")
        if not isinstance(entries_raw, list):
            raise ValueError(
                f"entries must be a list in schedule file, got {type(entries_raw).__name__}"
            )
        if not entries_raw:
            raise ValueError("Schedule file must have at least one entry")

        entries: list[BlindScheduleEntry] = []
        for i, entry_data in enumerate(entries_raw):
            if not isinstance(entry_data, dict):
                raise ValueError(
                    f"entries[{i}] must be a JSON object, got {type(entry_data).__name__}"
                )

            level_data = extractor.get_required_dict(
                entry_data, "level", context=f"entries[{i}]"
            )
            small_blind_value = extractor.get_required_int(
                level_data, "small_blind", context=f"entries[{i}].level"
            )
            big_blind_value = extractor.get_required_int(
                level_data, "big_blind", context=f"entries[{i}].level"
            )
            level_number = extractor.get_required_int(
                level_data, "level", context=f"entries[{i}].level"
            )

            start_hand = extractor.get_required_int(
                entry_data, "start_hand", context=f"entries[{i}]"
            )
            duration_hands = extractor.get_required_int(
                entry_data, "duration_hands", context=f"entries[{i}]"
            )

            blind_level = BlindLevel(
                small_blind=ChipAmount(small_blind_value),
                big_blind=ChipAmount(big_blind_value),
                level=level_number,
            )

            entry = BlindScheduleEntry(
                level=blind_level,
                start_hand=start_hand,
                duration_hands=duration_hands,
            )
            entries.append(entry)

        config = BlindSchedule(entries=tuple(entries))
        self._logger.info(
            "blind_schedule_config_loaded",
            path=str(self._config_path),
            num_entries=len(config.entries),
        )
        return config
