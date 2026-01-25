"""Utility functions for environment detection."""

import json
import os

import structlog

from src.constants.config import ENVIRONMENT_CONFIG_PATH
from src.core.enums import ApplicationEnvironment

_logger = structlog.get_logger(__name__.removeprefix("src."))


def load_environment_name(
    logger: structlog.BoundLogger | None = None,
) -> ApplicationEnvironment:
    """Resolve the current application environment from env vars or config/environment.json.

    Args:
        logger: Optional logger for logging resolution steps and failures.
            If not provided, uses module-level logger.

    Returns:
        ApplicationEnvironment enum. Defaults to ApplicationEnvironment.DEVELOPMENT.
    """
    active_logger = logger or _logger

    env_override = os.getenv("CLANKER_ENV")
    if env_override:
        try:
            env = ApplicationEnvironment(env_override.lower())
            active_logger.info(
                "environment_resolved_from_env_var",
                env_var="CLANKER_ENV",
                environment=env.value,
            )
            return env
        except ValueError:
            active_logger.warning(
                "environment_invalid_from_env_var",
                env_var="CLANKER_ENV",
                value=env_override,
                default="development",
            )

    env_config_path = ENVIRONMENT_CONFIG_PATH
    if env_config_path.exists():
        try:
            with env_config_path.open("r", encoding="utf-8") as f:
                payload: dict[str, object] = json.load(f)
            candidate = payload.get("environment")
            if isinstance(candidate, str):
                try:
                    env = ApplicationEnvironment(candidate.lower())
                    active_logger.info(
                        "environment_resolved_from_config_file",
                        config_path=str(env_config_path),
                        environment=env.value,
                    )
                    return env
                except ValueError:
                    active_logger.warning(
                        "environment_invalid_in_config_file",
                        config_path=str(env_config_path),
                        value=candidate,
                        default="development",
                    )
            else:
                active_logger.warning(
                    "environment_config_invalid_format",
                    config_path=str(env_config_path),
                    reason="'environment' key missing or not a string",
                )
        except json.JSONDecodeError as e:
            active_logger.warning(
                "environment_config_invalid_json",
                config_path=str(env_config_path),
                error=str(e),
            )
        except (KeyError, ValueError, OSError) as e:
            active_logger.warning(
                "environment_config_read_failed",
                config_path=str(env_config_path),
                error=str(e),
                error_type=type(e).__name__,
            )
    else:
        active_logger.debug(
            "environment_config_file_not_found",
            config_path=str(env_config_path),
        )

    active_logger.info(
        "environment_using_default",
        default="development",
        reason="No CLANKER_ENV env var and config file unavailable or invalid",
    )
    return ApplicationEnvironment.DEVELOPMENT
