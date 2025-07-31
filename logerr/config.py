"""
Configuration system for logerr using confection.

Provides configurable logging behavior for Result/Option error cases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from confection import Config

if TYPE_CHECKING:
    from .result import Result


@dataclass
class LoggingConfig:
    """Configuration for error logging behavior."""

    # Global logging settings
    enabled: bool = True
    level: str = "ERROR"
    format: str | None = None

    # Per-library settings
    libraries: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Context capture settings
    capture_function_name: bool = True
    capture_filename: bool = True
    capture_lineno: bool = True
    capture_locals: bool = False


# Global configuration instance
_config: LoggingConfig | None = None


def get_config() -> LoggingConfig:
    """Get the current logging configuration."""
    global _config
    if _config is None:
        _config = LoggingConfig()
    return _config


def reset_config() -> None:
    """Reset configuration to defaults."""
    global _config
    _config = LoggingConfig()


def configure(config_dict: dict[str, Any]) -> Result[None, ValueError]:
    """
    Configure logerr from a dictionary.

    Args:
        config_dict: Configuration dictionary that can include:
            - enabled: bool - Enable/disable logging
            - level: str - Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            - format: str - Custom log format
            - libraries: dict - Per-library configuration
            - capture_*: bool - Context capture settings

    Returns:
        Ok(None) if configuration was applied successfully,
        Err(ValueError) if invalid configuration values provided
    """
    # Import at runtime to avoid circular import
    from .result import Result

    global _config

    # Use functional API pipeline for validation and configuration creation
    level = config_dict.get("level", get_config().level)
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

    def _create_and_set_config() -> None:
        """Create new configuration from dictionary and set it globally."""
        global _config
        current = get_config()
        _config = LoggingConfig(
            enabled=config_dict.get("enabled", current.enabled),
            level=level,
            format=config_dict.get("format", current.format),
            libraries={**current.libraries, **config_dict.get("libraries", {})},
            capture_function_name=config_dict.get(
                "capture_function_name", current.capture_function_name
            ),
            capture_filename=config_dict.get(
                "capture_filename", current.capture_filename
            ),
            capture_lineno=config_dict.get("capture_lineno", current.capture_lineno),
            capture_locals=config_dict.get("capture_locals", current.capture_locals),
        )

    return Result.from_predicate(
        level,
        lambda lvl: lvl in valid_levels,
        ValueError(f"Invalid log level '{level}'. Must be one of: {valid_levels}"),
    ).and_then(
        lambda _: Result.from_callable(_create_and_set_config).map_err(ValueError)
    )


def configure_from_confection(config_path: str) -> Result[None, Exception]:
    """
    Configure logerr from a confection config file.

    Args:
        config_path: Path to the configuration file

    Returns:
        Ok(None) if configuration was loaded successfully,
        Err(Exception) if file loading or parsing failed
    """
    # Import at runtime to avoid circular import
    from .option import Option
    from .result import Ok, Result

    # Use functional API pipeline with inline lambdas for simple operations
    def _safe_configure(logerr_config: dict[str, Any]) -> Result[None, Exception]:
        """Safely configure with consistent error type."""
        return configure(logerr_config).map_err(lambda e: Exception(str(e)))

    return (
        Result.from_predicate(
            config_path,
            lambda path: Path(path).exists(),
            Exception(f"Config file not found: {config_path}"),
        )
        .and_then(lambda path: Result.from_callable(lambda: Config().from_disk(path)))
        .and_then(
            lambda config: Option.from_nullable(config.get("logerr"))
            .map(_safe_configure)
            .unwrap_or(Ok(None))
        )
    )


def get_library_config(library_name: str) -> dict[str, Any]:
    """
    Get configuration for a specific library.

    Args:
        library_name: Name of the library

    Returns:
        Configuration dictionary for the library
    """
    # Note: Don't use Option here as it would cause recursion during logging
    config = get_config()
    return config.libraries.get(library_name, {})


def should_log_for_library(library_name: str) -> bool:
    """
    Check if logging is enabled for a specific library.

    Args:
        library_name: Name of the library

    Returns:
        True if logging should occur for this library
    """
    config = get_config()
    if not config.enabled:
        return False

    lib_config = get_library_config(library_name)
    enabled = lib_config.get("enabled", True)
    return bool(enabled)


def get_log_level_for_library(library_name: str) -> str:
    """
    Get the log level for a specific library.

    Args:
        library_name: Name of the library

    Returns:
        Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    config = get_config()
    lib_config = get_library_config(library_name)
    level = lib_config.get("level", config.level)
    return str(level)


# TODO: Add confection registry integration later
# For now, configuration works through the direct API
