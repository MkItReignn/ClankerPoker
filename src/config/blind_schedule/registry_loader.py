"""Blind schedule mode registry loader.

Loads the blind schedule mode registry from the main config file,
which references individual schedule files for each mode.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, final, override

import structlog

from src.config.base.config_loader import BaseConfigLoader
from src.config.blind_schedule.config import BlindSchedule, BlindScheduleRegistry
from src.config.blind_schedule.config_loader import BlindScheduleLoader
from src.config.utils.type_extractors import ConfigTypeExtractor
from src.logger.factories import get_generic_logger


@final
class BlindScheduleRegistryLoader(BaseConfigLoader[BlindScheduleRegistry]):
    """Loads blind schedule mode registry from main config file.

    Loads the registry that contains all available blind schedule modes.
    Each mode is loaded from its individual schedule file using BlindScheduleLoader.
    """

    def __init__(
        self,
        config_path: Path | None = None,
        logger: structlog.BoundLogger | None = None,
        *,
        json_loader: Any = None,
        schedule_config_loader: type[BlindScheduleLoader] | None = None,
    ) -> None:
        """Initialize blind schedule mode registry loader.

        Args:
            config_path: Path to main config file. Defaults to BLIND_SCHEDULE_CONFIG_PATH.
            logger: Optional logger. Defaults to creating one.
            json_loader: Optional JSON loader (for testing).
            schedule_config_loader: Optional schedule config loader class (for testing).
        """
        from src.constants.config import BLIND_SCHEDULE_CONFIG_PATH

        resolved_path = config_path or BLIND_SCHEDULE_CONFIG_PATH
        resolved_logger = logger or get_generic_logger(__name__.removeprefix("src."))
        super().__init__(
            config_path=resolved_path,
            logger=resolved_logger,
            json_loader=json_loader,
        )
        # Store schedules directory path
        self._schedules_dir = resolved_path.parent / "schedules"
        self._schedule_config_loader_class = schedule_config_loader or BlindScheduleLoader

    @override
    def _load_config(self) -> BlindScheduleRegistry:
        """Load blind schedule mode registry with all modes.

        Returns:
            BlindScheduleRegistry with all modes loaded.

        Raises:
            FileNotFoundError: If config file or schedule files do not exist.
            ValueError: If config cannot be parsed or required fields are missing.
        """
        # Load main config
        main_payload = self._json_loader.load()
        extractor = ConfigTypeExtractor(logger=self._logger)

        default_mode = extractor.get_required_string(
            main_payload, "default_mode", context="root"
        )

        modes_config = extractor.get_dict_or_default(
            main_payload, "modes", default={}, context="root"
        )

        if not modes_config:
            raise ValueError("At least one mode must be defined in 'modes'")

        # Load all schedule modes using BlindScheduleLoader
        modes: dict[str, BlindSchedule] = {}

        for mode_name, mode_info in modes_config.items():
            if not isinstance(mode_info, dict):
                raise ValueError(
                    f"modes['{mode_name}'] must be a JSON object, "
                    f"got {type(mode_info).__name__}"
                )

            schedule_file = extractor.get_required_string(
                mode_info, "file", context=f"modes['{mode_name}']"
            )

            schedule_path = self._schedules_dir / schedule_file

            # Use BlindScheduleLoader to load individual schedule
            schedule_loader = self._schedule_config_loader_class(
                config_path=schedule_path,
                logger=self._logger,
            )
            schedule_config = schedule_loader.load()
            modes[mode_name] = schedule_config

            self._logger.debug(
                "blind_schedule_mode_loaded",
                mode=mode_name,
                schedule_file=str(schedule_path),
                num_entries=len(schedule_config.entries),
            )

        registry = BlindScheduleRegistry(
            modes=modes,
            default_mode=default_mode,
        )

        self._logger.info(
            "blind_schedule_registry_loaded",
            default_mode=default_mode,
            available_modes=list(modes.keys()),
            num_modes=len(modes),
        )

        return registry
