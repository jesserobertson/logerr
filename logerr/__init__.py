"""
logerr: Rust-like Option and Result types for Python with automatic logging.

A library that provides Option and Result types similar to Rust, with automatic
logging of errors using loguru, and configuration management via confection.
"""

__version__ = "0.1.0"

# Re-export main types
from .result import Result, Ok, Err
from .option import Option, Some, Nothing
from .config import configure, configure_from_confection, get_config, reset_config

# Import modules for namespaced factory functions
from . import result
from . import option

__all__ = [
    "Result", "Ok", "Err", 
    "Option", "Some", "Nothing",
    "configure", "configure_from_confection", "get_config", "reset_config",
    "result", "option"
]