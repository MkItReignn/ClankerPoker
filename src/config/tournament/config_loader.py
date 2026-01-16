"""Tournament configuration loader.

Loads tournament configuration from JSON files.
Configuration files are located at the project root in config/tournament/.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, final, override

import structlog

from src.config.base.config_loader import BaseConfigLoader
from src.config.blind_schedule.registry_loader import BlindScheduleRegistryLoader
from src.config.tournament.config import PayoutStructure, TournamentConfig
from src.config.utils.type_extractors import ConfigTypeExtractor
from src.constants.config import BLIND_SCHEDULE_CONFIG_PATH, TOURNAMENT_CONFIG_PATH
from src.domain.models.chips import ChipAmount
from src.logger.factories import get_generic_logger


@final
class TournamentConfigLoader(BaseConfigLoader[TournamentConfig]):
    """Loads tournament configuration from JSON."""

    def __init__(
        self,
        config_path: Path | None = None,
        logger: structlog.BoundLogger | None = None,
        *,
        json_loader: Any = None,
        blind_schedule_loader: BlindScheduleRegistryLoader | None = None,
    ) -> None:
        """Initialize tournament config loader.

        Args:
            config_path: Path to config file. Defaults to TOURNAMENT_CONFIG_PATH.
            logger: Optional logger. Defaults to creating one.
            json_loader: Optional JSON loader (for testing).
            blind_schedule_loader: Optional blind schedule registry loader (for testing).
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
            ValueError: If config cannot be parsed, required fields are missing,
                or blind schedule cannot be loaded.
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

        # Blind schedule is required - fail if not found
        loader = self._blind_schedule_loader or BlindScheduleRegistryLoader(
            config_path=BLIND_SCHEDULE_CONFIG_PATH,
            logger=self._logger,
        )
        try:
            registry = loader.load()
            blind_schedule = registry.get_default()
        except FileNotFoundError as e:
            self._logger.error(
                "blind_schedule_config_required",
                path=str(BLIND_SCHEDULE_CONFIG_PATH),
                error=str(e),
            )
            raise ValueError(
                f"Blind schedule configuration is required but not found: {BLIND_SCHEDULE_CONFIG_PATH}"
            ) from e

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
        )
        return config
