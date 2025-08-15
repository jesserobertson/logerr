"""Type stubs for logerr.config module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .result import Result

@dataclass
class LoggingConfig:
    """Basic configuration for error logging behavior."""

    enabled: bool
    level: str

    def __init__(self, enabled: bool = True, level: str = "ERROR") -> None: ...

def get_config() -> LoggingConfig:
    """Get the current logging configuration."""
    ...

def reset_config() -> None:
    """Reset configuration to defaults."""
    ...

def configure(
    enabled: bool | None = None, level: str | None = None
) -> Result[None, ValueError]:
    """Configure logerr with basic settings."""
    ...

def should_log() -> bool:
    """Check if logging is enabled."""
    ...

def get_log_level() -> str:
    """Get the current log level."""
    ...
