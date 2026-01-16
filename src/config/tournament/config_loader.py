"""Tournament configuration loader.

Loads tournament configuration from JSON files.
Configuration files are located at the project root in config/tournament/.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, final, override

import structlog

from src.config.base.config_loader import BaseConfigLoader
from src.config.tournament.config import (BlindScheduleConfig,
                                          BlindScheduleEntry, PayoutStructure,
                                          TournamentConfig)
from src.config.utils.type_extractors import ConfigTypeExtractor
from src.constants.config import (BLIND_SCHEDULE_CONFIG_PATH,
                                  TOURNAMENT_CONFIG_PATH)
from src.domain.models.blinds import BlindLevel
from src.domain.models.chips import ChipAmount
from src.logger.factories import get_generic_logger


@final
class BlindScheduleConfigLoader(BaseConfigLoader[BlindScheduleConfig]):
    """Loads blind schedule configuration from JSON."""

    def __init__(
        self,
        config_path: Path | None = None,
        logger: structlog.BoundLogger | None = None,
        *,
        json_loader: Any = None,
    ) -> None:
        """Initialize blind schedule config loader.

        Args:
            config_path: Path to config file. Defaults to BLIND_SCHEDULE_CONFIG_PATH.
            logger: Optional logger. Defaults to creating one.
            json_loader: Optional JSON loader (for testing).
        """
        resolved_path = config_path or BLIND_SCHEDULE_CONFIG_PATH
        resolved_logger = logger or get_generic_logger(__name__.removeprefix("src."))
        super().__init__(
            config_path=resolved_path,
            logger=resolved_logger,
            json_loader=json_loader,
        )

    @override
    def _load_config(self) -> BlindScheduleConfig:
        """Load blind schedule configuration from JSON.

        Returns:
            BlindScheduleConfig object.

        Raises:
            FileNotFoundError: If config file does not exist.
            ValueError: If config cannot be parsed or required fields are missing.
        """
        payload = self._json_loader.load()
        extractor = ConfigTypeExtractor(logger=self._logger)

        entries_raw = payload.get("entries")
        if entries_raw is None:
            raise ValueError("entries is required in configuration")
        if not isinstance(entries_raw, list):
            raise ValueError("entries must be a list")
        if not entries_raw:
            raise ValueError("Blind schedule must have at least one entry")

        entries: list[BlindScheduleEntry] = []
        for i, entry_data in enumerate(entries_raw):
            if not isinstance(entry_data, dict):
                raise ValueError(
                    f"entries[{i}] must be a JSON object, got {type(entry_data).__name__}"
                )
            level_data = extractor.get_required_dict(entry_data, "level", context=f"entries[{i}]")
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

        config = BlindScheduleConfig(entries=tuple(entries))
        self._logger.info(
            "blind_schedule_config_loaded",
            num_entries=len(config.entries),
        )
        return config


@final
class TournamentConfigLoader(BaseConfigLoader[TournamentConfig]):
    """Loads tournament configuration from JSON."""

    def __init__(
        self,
        config_path: Path | None = None,
        logger: structlog.BoundLogger | None = None,
        *,
        json_loader: Any = None,
        blind_schedule_loader: BlindScheduleConfigLoader | None = None,
    ) -> None:
        """Initialize tournament config loader.

        Args:
            config_path: Path to config file. Defaults to TOURNAMENT_CONFIG_PATH.
            logger: Optional logger. Defaults to creating one.
            json_loader: Optional JSON loader (for testing).
            blind_schedule_loader: Optional blind schedule loader (for testing).
        """
        resolved_path = config_path or TOURNAMENT_CONFIG_PATH
        resolved_logger = logger or get_generic_logger(__name__.removeprefix("src."))
        super().__init__(
            config_path=resolved_path,
            logger=resolved_logger,
            json_loader=json_loader,
        )
        self._blind_schedule_loader = blind_schedule_loader

    @override
    def _load_config(self) -> TournamentConfig:
        """Load tournament configuration from JSON.

        Returns:
            TournamentConfig object.

        Raises:
            FileNotFoundError: If config file does not exist.
            ValueError: If config cannot be parsed or required fields are missing.
        """
        payload = self._json_loader.load()
        extractor = ConfigTypeExtractor(logger=self._logger)

        buy_in_amount = ChipAmount(extractor.get_required_int(payload, "buy_in_amount"))
        starting_chip_stack = ChipAmount(extractor.get_required_int(payload, "starting_chip_stack"))
        payout_structure_str = extractor.get_required_string(payload, "payout_structure")

        try:
            payout_structure = PayoutStructure(payout_structure_str)
        except ValueError:
            valid_values = [e.value for e in PayoutStructure]
            raise ValueError(
                f"Invalid payout_structure: {payout_structure_str}. "
                f"Valid values: {valid_values}"
            )

        blind_schedule: BlindScheduleConfig | None = None
        try:
            loader = self._blind_schedule_loader or BlindScheduleConfigLoader(
                config_path=BLIND_SCHEDULE_CONFIG_PATH,
                logger=self._logger,
            )
            blind_schedule = loader.load()
        except FileNotFoundError:
            self._logger.debug(
                "blind_schedule_config_not_found",
                path=str(BLIND_SCHEDULE_CONFIG_PATH),
            )
            blind_schedule = None

        config = TournamentConfig(
            buy_in_amount=buy_in_amount,
            starting_chip_stack=starting_chip_stack,
            payout_structure=payout_structure,
            blind_schedule=blind_schedule,
        )
        self._logger.info(
            "tournament_config_loaded",
            buy_in=buy_in_amount.value,
            starting_chips=starting_chip_stack.value,
            payout_structure=payout_structure.value,
            has_blind_schedule=blind_schedule is not None,
        )
        return config
