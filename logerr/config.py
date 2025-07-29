"""
Configuration system for logerr using confection.

Provides configurable logging behavior for Result/Option error cases.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from confection import Config


@dataclass
class LoggingConfig:
    """Configuration for error logging behavior."""

    # Global logging settings
    enabled: bool = True
    level: str = "ERROR"
    format: Optional[str] = None

    # Per-library settings
    libraries: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Context capture settings
    capture_function_name: bool = True
    capture_filename: bool = True
    capture_lineno: bool = True
    capture_locals: bool = False


# Global configuration instance
_config: Optional[LoggingConfig] = None


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


def configure(config_dict: Dict[str, Any]) -> None:
    """
    Configure logerr from a dictionary.

    Args:
        config_dict: Configuration dictionary that can include:
            - enabled: bool - Enable/disable logging
            - level: str - Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            - format: str - Custom log format
            - libraries: dict - Per-library configuration
            - capture_*: bool - Context capture settings
    """
    global _config

    # Create new config from current + updates
    current = get_config()

    _config = LoggingConfig(
        enabled=config_dict.get("enabled", current.enabled),
        level=config_dict.get("level", current.level),
        format=config_dict.get("format", current.format),
        libraries={**current.libraries, **config_dict.get("libraries", {})},
        capture_function_name=config_dict.get(
            "capture_function_name", current.capture_function_name
        ),
        capture_filename=config_dict.get("capture_filename", current.capture_filename),
        capture_lineno=config_dict.get("capture_lineno", current.capture_lineno),
        capture_locals=config_dict.get("capture_locals", current.capture_locals),
    )


def configure_from_confection(config_path: str) -> None:
    """
    Configure logerr from a confection config file.

    Args:
        config_path: Path to the configuration file
    """
    config = Config().from_disk(config_path)
    if "logerr" in config:
        configure(config["logerr"])


def get_library_config(library_name: str) -> Dict[str, Any]:
    """
    Get configuration for a specific library.

    Args:
        library_name: Name of the library

    Returns:
        Configuration dictionary for the library
    """
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
    return lib_config.get("enabled", True)


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
    return lib_config.get("level", config.level)


# TODO: Add confection registry integration later
# For now, configuration works through the direct API
