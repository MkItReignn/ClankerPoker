"""Shared utilities for extracting and validating types from config dictionaries."""

from typing import TypeVar, final

import structlog

T = TypeVar("T", str, int, float, bool)


@final
class ConfigTypeExtractor:
    """Extracts and validates types from configuration dictionaries."""

    def __init__(self, logger: structlog.BoundLogger) -> None:
        """Initialize type extractor.

        Args:
            logger: Logger for logging validation warnings and errors (required).
        """
        self._logger = logger

    def get_required_bool(
        self,
        data: dict[str, object],
        key: str,
        *,
        context: str | None = None,
    ) -> bool:
        """Extract required boolean value from config dict.

        Args:
            data: Configuration dictionary to extract from.
            key: Key to extract (must exist).
            context: Optional context string for error messages (e.g., platform name).

        Returns:
            Boolean value from config.

        Raises:
            ValueError: If key is missing or value is not a boolean.
        """
        if key not in data:
            context_prefix = f"{context}: " if context else ""
            error_msg = f"{context_prefix}'{key}' is required but missing from configuration"
            self._logger.error(
                "config_required_field_missing",
                key=key,
                context=context,
            )
            raise ValueError(error_msg)

        value = data[key]
        if not isinstance(value, bool):
            context_prefix = f"{context}: " if context else ""
            error_msg = f"{context_prefix}'{key}' must be a boolean, got {type(value).__name__}"
            self._logger.error(
                "config_validation_error",
                key=key,
                expected_type="bool",
                actual_type=type(value).__name__,
                context=context,
            )
            raise ValueError(error_msg)
        return value

    def get_required_int(
        self,
        data: dict[str, object],
        key: str,
        *,
        context: str | None = None,
    ) -> int:
        """Extract required integer value from config dict.

        Args:
            data: Configuration dictionary to extract from.
            key: Key to extract (must exist).
            context: Optional context string for error messages (e.g., platform name).

        Returns:
            Integer value from config.

        Raises:
            ValueError: If key is missing or value is not an integer.
        """
        if key not in data:
            context_prefix = f"{context}: " if context else ""
            error_msg = f"{context_prefix}'{key}' is required but missing from configuration"
            self._logger.error(
                "config_required_field_missing",
                key=key,
                context=context,
            )
            raise ValueError(error_msg)

        value = data[key]
        if not isinstance(value, int):
            context_prefix = f"{context}: " if context else ""
            error_msg = f"{context_prefix}'{key}' must be an integer, got {type(value).__name__}"
            self._logger.error(
                "config_validation_error",
                key=key,
                expected_type="int",
                actual_type=type(value).__name__,
                context=context,
            )
            raise ValueError(error_msg)
        return value

    def get_int_or_none(
        self,
        data: dict[str, object],
        key: str,
        *,
        context: str | None = None,
    ) -> int | None:
        """Extract integer or None from config dict.

        Args:
            data: Configuration dictionary to extract from.
            key: Key to extract.
            context: Optional context string for error messages (e.g., platform name).

        Returns:
            Integer value from config, None if key is missing or value is null.

        Raises:
            ValueError: If key exists with non-null value that is not an integer.
        """
        if key not in data:
            return None

        value = data[key]
        if value is None:
            return None

        if not isinstance(value, int):
            context_prefix = f"{context}: " if context else ""
            error_msg = (
                f"{context_prefix}'{key}' must be an integer or null, got {type(value).__name__}"
            )
            self._logger.error(
                "config_validation_error",
                key=key,
                expected_type="int | None",
                actual_type=type(value).__name__,
                context=context,
            )
            raise ValueError(error_msg)
        return value

    def get_float_or_none(
        self,
        data: dict[str, object],
        key: str,
        *,
        context: str | None = None,
    ) -> float | None:
        """Extract float or None from config dict.

        Args:
            data: Configuration dictionary to extract from.
            key: Key to extract.
            context: Optional context string for error messages (e.g., platform name).

        Returns:
            Float value from config, None if key is missing or value is null.
            Accepts both int and float values, converting int to float.

        Raises:
            ValueError: If key exists with non-null value that is not a number.
        """
        if key not in data:
            return None

        value = data[key]
        if value is None:
            return None

        if isinstance(value, int | float):
            return float(value)

        context_prefix = f"{context}: " if context else ""
        error_msg = f"{context_prefix}'{key}' must be a number or null, got {type(value).__name__}"
        self._logger.error(
            "config_validation_error",
            key=key,
            expected_type="float | None",
            actual_type=type(value).__name__,
            context=context,
        )
        raise ValueError(error_msg)

    def get_required_float(
        self,
        data: dict[str, object],
        key: str,
        *,
        context: str | None = None,
    ) -> float:
        """Extract required float value from config dict.

        Args:
            data: Configuration dictionary to extract from.
            key: Key to extract (must exist).
            context: Optional context string for error messages (e.g., platform name).

        Returns:
            Float value from config. Accepts both int and float values, converting int to float.

        Raises:
            ValueError: If key is missing or value is not a number (int or float).
        """
        if key not in data:
            context_prefix = f"{context}: " if context else ""
            error_msg = f"{context_prefix}'{key}' is required but missing from configuration"
            self._logger.error(
                "config_required_field_missing",
                key=key,
                context=context,
            )
            raise ValueError(error_msg)

        value = data[key]
        if isinstance(value, int | float):
            return float(value)

        context_prefix = f"{context}: " if context else ""
        error_msg = f"{context_prefix}'{key}' must be a number, got {type(value).__name__}"
        self._logger.error(
            "config_validation_error",
            key=key,
            expected_type="float",
            actual_type=type(value).__name__,
            context=context,
        )
        raise ValueError(error_msg)

    def get_required_string(
        self,
        data: dict[str, object],
        key: str,
        *,
        context: str | None = None,
    ) -> str:
        """Extract required string value from config dict.

        Args:
            data: Configuration dictionary to extract from.
            key: Key to extract (must exist).
            context: Optional context string for error messages (e.g., platform name).

        Returns:
            String value from config.

        Raises:
            ValueError: If key is missing or value is not a string.
        """
        if key not in data:
            context_prefix = f"{context}: " if context else ""
            error_msg = f"{context_prefix}'{key}' is required but missing from configuration"
            self._logger.error(
                "config_required_field_missing",
                key=key,
                context=context,
            )
            raise ValueError(error_msg)

        value = data[key]
        if not isinstance(value, str):
            context_prefix = f"{context}: " if context else ""
            error_msg = f"{context_prefix}'{key}' must be a string, got {type(value).__name__}"
            self._logger.error(
                "config_validation_error",
                key=key,
                expected_type="str",
                actual_type=type(value).__name__,
                context=context,
            )
            raise ValueError(error_msg)
        return value

    def get_string_with_default(
        self,
        data: dict[str, object],
        key: str,
        default: str,
        *,
        context: str | None = None,
    ) -> str:
        """Extract string value from config dict with default fallback.

        Args:
            data: Configuration dictionary to extract from.
            key: Key to extract.
            default: Default value to return if key is missing.
            context: Optional context string for error messages.

        Returns:
            String value from config, or default if key is missing.

        Raises:
            ValueError: If key exists but value is not a string.
        """
        if key not in data:
            return default
        return self.get_required_string(data, key, context=context)

    def get_float_with_default(
        self,
        data: dict[str, object],
        key: str,
        default: float,
        *,
        context: str | None = None,
    ) -> float:
        """Extract float value from config dict with default fallback.

        Args:
            data: Configuration dictionary to extract from.
            key: Key to extract.
            default: Default value to return if key is missing.
            context: Optional context string for error messages.

        Returns:
            Float value from config, or default if key is missing.
            Accepts both int and float values, converting int to float.

        Raises:
            ValueError: If key exists but value is not a number.
        """
        if key not in data:
            return default
        return self.get_required_float(data, key, context=context)

    def get_str_or_none(
        self,
        data: dict[str, object],
        key: str,
        *,
        context: str | None = None,
    ) -> str | None:
        """Extract string or None from config dict.

        Args:
            data: Configuration dictionary to extract from.
            key: Key to extract.
            context: Optional context string for error messages (e.g., platform name).

        Returns:
            String value from config, None if key is missing or value is null.

        Raises:
            ValueError: If key exists with non-null value that is not a string.
        """
        if key not in data:
            return None

        value = data[key]
        if value is None:
            return None

        if not isinstance(value, str):
            context_prefix = f"{context}: " if context else ""
            error_msg = (
                f"{context_prefix}'{key}' must be a string or null, got {type(value).__name__}"
            )
            self._logger.error(
                "config_validation_error",
                key=key,
                expected_type="str | None",
                actual_type=type(value).__name__,
                context=context,
            )
            raise ValueError(error_msg)
        return value

    def get_required_dict(
        self,
        data: dict[str, object],
        key: str,
        *,
        context: str | None = None,
    ) -> dict[str, object]:
        """Extract required dictionary value from config dict.

        Args:
            data: Configuration dictionary to extract from.
            key: Key to extract (must exist).
            context: Optional context string for error messages (e.g., platform name).

        Returns:
            Dictionary value from config.

        Raises:
            ValueError: If key is missing or value is not a dictionary.
        """
        if key not in data:
            context_prefix = f"{context}: " if context else ""
            error_msg = f"{context_prefix}'{key}' is required but missing from configuration"
            self._logger.error(
                "config_required_field_missing",
                key=key,
                context=context,
            )
            raise ValueError(error_msg)

        value = data[key]
        if not isinstance(value, dict):
            context_prefix = f"{context}: " if context else ""
            error_msg = f"{context_prefix}'{key}' must be a JSON object, got {type(value).__name__}"
            self._logger.error(
                "config_validation_error",
                key=key,
                expected_type="dict",
                actual_type=type(value).__name__,
                context=context,
            )
            raise ValueError(error_msg)
        return value

    def get_dict_or_default(
        self,
        data: dict[str, object],
        key: str,
        default: dict[str, object],
        *,
        context: str | None = None,
    ) -> dict[str, object]:
        """Extract dictionary value from config dict with default fallback.

        Args:
            data: Configuration dictionary to extract from.
            key: Key to extract.
            default: Default value to return if key is missing.
            context: Optional context string for error messages.

        Returns:
            Dictionary value from config, or default if key is missing.

        Raises:
            ValueError: If key exists but value is not a dictionary.
        """
        if key not in data:
            return default
        return self.get_required_dict(data, key, context=context)

    def get_dict_or_none(
        self,
        data: dict[str, object],
        key: str,
        *,
        context: str | None = None,
    ) -> dict[str, object] | None:
        """Extract dictionary or None from config dict.

        Args:
            data: Configuration dictionary to extract from.
            key: Key to extract.
            context: Optional context string for error messages (e.g., platform name).

        Returns:
            Dictionary value from config, None if key is missing or value is null.

        Raises:
            ValueError: If key exists with non-null value that is not a dictionary.
        """
        if key not in data:
            return None

        value = data[key]
        if value is None:
            return None

        if not isinstance(value, dict):
            context_prefix = f"{context}: " if context else ""
            error_msg = (
                f"{context_prefix}'{key}' must be a JSON object or null, got {type(value).__name__}"
            )
            self._logger.error(
                "config_validation_error",
                key=key,
                expected_type="dict | None",
                actual_type=type(value).__name__,
                context=context,
            )
            raise ValueError(error_msg)
        return value

    def get_required_list_of(
        self,
        data: dict[str, object],
        key: str,
        element_type: type[T],
        *,
        context: str | None = None,
    ) -> list[T]:
        """Extract required list of specific type from config dict.

        Args:
            data: Configuration dictionary to extract from.
            key: Key to extract (must exist).
            element_type: Expected type for list elements. Must be one of: str, int, float, bool.
            context: Optional context string for error messages.

        Returns:
            List of elements of the specified type.

        Raises:
            ValueError: If key is missing, value is not a list, or elements are not of the expected type.
            TypeError: If element_type is not one of the allowed types (str, int, float, bool).
        """
        allowed_types = {str, int, float, bool}
        if element_type not in allowed_types:
            raise TypeError(f"element_type must be one of {allowed_types}, got {element_type}")

        if key not in data:
            context_prefix = f"{context}: " if context else ""
            error_msg = f"{context_prefix}'{key}' is required but missing from configuration"
            self._logger.error(
                "config_required_field_missing",
                key=key,
                context=context,
            )
            raise ValueError(error_msg)

        value = data[key]
        if not isinstance(value, list):
            context_prefix = f"{context}: " if context else ""
            error_msg = f"{context_prefix}'{key}' must be a list, got {type(value).__name__}"
            self._logger.error(
                "config_validation_error",
                key=key,
                expected_type="list",
                actual_type=type(value).__name__,
                context=context,
            )
            raise ValueError(error_msg)

        result: list[T] = []
        for i, item in enumerate(value):
            if not isinstance(item, element_type):
                context_prefix = f"{context}: " if context else ""
                type_name = element_type.__name__
                error_msg = (
                    f"{context_prefix}'{key}[{i}]' must be a {type_name}, "
                    f"got {type(item).__name__}"
                )
                self._logger.error(
                    "config_validation_error",
                    key=f"{key}[{i}]",
                    expected_type=type_name,
                    actual_type=type(item).__name__,
                    context=context,
                )
                raise ValueError(error_msg)
            result.append(item)

        return result
