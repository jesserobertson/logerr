"""
Simplified core configuration system for logerr.

Provides basic logging control for Result/Option error cases.
For advanced configuration features, see logerr.recipes.config
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .result import Result


@dataclass
class LoggingConfig:
    """Basic configuration for error logging behavior."""

    # Core settings - kept simple
    enabled: bool = True
    level: str = "ERROR"


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


def configure(
    enabled: bool | None = None, level: str | None = None
) -> Result[None, ValueError]:
    """
    Configure logerr with basic settings.

    Args:
        enabled: Enable/disable logging (default: True)
        level: Log level - DEBUG, INFO, WARNING, ERROR, CRITICAL (default: ERROR)

    Returns:
        Ok(None) if configuration was applied successfully,
        Err(ValueError) if invalid configuration values provided

    Examples:
        >>> import logerr
        >>> logerr.configure(enabled=True, level="WARNING")  # doctest: +SKIP
        >>> logerr.configure(level="INFO")  # doctest: +SKIP
    """
    # Import at runtime to avoid circular import
    from .result import Err, Ok

    global _config
    current = get_config()

    # Validate log level if provided
    if level is not None:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if level not in valid_levels:
            return Err.from_value(
                ValueError(
                    f"Invalid log level '{level}'. Must be one of: {valid_levels}"
                )
            )

    # Apply configuration
    _config = LoggingConfig(
        enabled=enabled if enabled is not None else current.enabled,
        level=level if level is not None else current.level,
    )

    return Ok(None)


def should_log() -> bool:
    """Check if logging is enabled."""
    return get_config().enabled


def get_log_level() -> str:
    """Get the current log level."""
    return get_config().level
