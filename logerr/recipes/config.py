"""
Advanced configuration system for logerr.

Provides per-library configuration, context capture, and file-based configuration
using confection. This extends the basic configuration available in the core library.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from confection import Config

if TYPE_CHECKING:
    from ..result import Result


@dataclass
class AdvancedLoggingConfig:
    """Advanced configuration for error logging behavior."""

    # Global logging settings (extends core config)
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


# Global advanced configuration instance
_advanced_config: AdvancedLoggingConfig | None = None


def get_advanced_config() -> AdvancedLoggingConfig:
    """Get the current advanced logging configuration."""
    global _advanced_config
    if _advanced_config is None:
        _advanced_config = AdvancedLoggingConfig()
    return _advanced_config


def reset_advanced_config() -> None:
    """Reset advanced configuration to defaults."""
    global _advanced_config
    _advanced_config = AdvancedLoggingConfig()


def configure_advanced(config_dict: dict[str, Any]) -> Result[None, ValueError]:
    """
    Configure logerr with advanced settings.

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

    Examples:
        >>> from logerr.recipes.config import configure_advanced
        >>> config = {
        ...     "enabled": True,
        ...     "level": "WARNING",
        ...     "libraries": {
        ...         "my_module": {"level": "DEBUG"},
        ...         "third_party": {"enabled": False}
        ...     },
        ...     "capture_locals": True
        ... }
        >>> configure_advanced(config)  # doctest: +SKIP
    """
    # Import at runtime to avoid circular import
    from ..result import Result

    global _advanced_config

    # Use functional API pipeline for validation and configuration creation
    level = config_dict.get("level", get_advanced_config().level)
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

    def _create_and_set_config() -> None:
        """Create new configuration from dictionary and set it globally."""
        global _advanced_config
        current = get_advanced_config()
        _advanced_config = AdvancedLoggingConfig(
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

    Examples:
        >>> from logerr.recipes.config import configure_from_confection
        >>> configure_from_confection("config.cfg")  # doctest: +SKIP
    """
    # Import at runtime to avoid circular import
    from ..option import Option
    from ..result import Ok, Result

    # Use functional API pipeline with inline lambdas for simple operations
    def _safe_configure(logerr_config: dict[str, Any]) -> Result[None, Exception]:
        """Safely configure with consistent error type."""
        return configure_advanced(logerr_config).map_err(lambda e: Exception(str(e)))

    return (
        Result.from_predicate(
            config_path,
            lambda path: Path(path).exists(),
            Exception(f"Config file not found: {config_path}"),
        )
        .and_then(lambda path: Result.from_callable(lambda: Config().from_disk(path)))
        .and_then(
            lambda config: (
                Option.from_nullable(config.get("logerr"))
                .map(_safe_configure)
                .unwrap_or(Ok(None))
            )
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
    config = get_advanced_config()
    return config.libraries.get(library_name, {})


def should_log_for_library(library_name: str) -> bool:
    """
    Check if logging is enabled for a specific library.

    Args:
        library_name: Name of the library

    Returns:
        True if logging should occur for this library
    """
    config = get_advanced_config()
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
    config = get_advanced_config()
    lib_config = get_library_config(library_name)
    level = lib_config.get("level", config.level)
    return str(level)


def sync_core_config() -> None:
    """Synchronize core config with advanced config basic settings."""
    from ..config import configure as core_configure

    advanced = get_advanced_config()
    core_configure(enabled=advanced.enabled, level=advanced.level)
