"""
logerr: Rust-like Option and Result types for Python with automatic logging.

A library that provides Option and Result types similar to Rust, with automatic
logging of errors using loguru, and configuration management via confection.
"""

__version__ = "0.1.0"

# Re-export main types
from .result import Result, Ok, Err, result_from_callable, result_from_optional
from .config import configure, configure_from_confection, get_config

# Option will be implemented next
# from .option import Option, Some, Nothing

__all__ = [
    "Result", "Ok", "Err", 
    "result_from_callable", "result_from_optional",
    "configure", "configure_from_confection", "get_config"
]