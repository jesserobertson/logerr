"""
logerr: Rust-like Option and Result types for Python with automatic logging.

A library that provides Option and Result types similar to Rust, with automatic
logging of errors using loguru, and configuration management via confection.
"""

__version__ = "0.1.0"

# Re-export main types
from .result import Result, Ok, Err, result_from_callable, result_from_optional
from .option import Option, Some, Nothing, option_from_nullable, option_from_callable, option_from_predicate
from .config import configure, configure_from_confection, get_config, reset_config

__all__ = [
    "Result", "Ok", "Err", 
    "result_from_callable", "result_from_optional",
    "Option", "Some", "Nothing",
    "option_from_nullable", "option_from_callable", "option_from_predicate",
    "configure", "configure_from_confection", "get_config", "reset_config"
]