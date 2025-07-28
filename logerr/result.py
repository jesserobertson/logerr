"""
Result type implementation with automatic logging integration.

Provides Rust-like Result<T, E> types with automatic logging of error cases
through loguru, configurable via confection.
"""

from __future__ import annotations

import inspect
from typing import TypeVar, Generic, Union, Callable, Any, Optional, Type
from abc import ABC, abstractmethod

from loguru import logger

from .config import get_config, should_log_for_library, get_log_level_for_library

T = TypeVar('T')
E = TypeVar('E')
U = TypeVar('U')


class Result(Generic[T, E], ABC):
    """
    A type that represents either success (Ok) or failure (Err).
    
    Similar to Rust's Result<T, E> type, with automatic logging integration
    for error cases.
    """
    
    @abstractmethod
    def is_ok(self) -> bool:
        """Returns True if the result is Ok."""
        pass
    
    @abstractmethod
    def is_err(self) -> bool:
        """Returns True if the result is Err."""
        pass
    
    @abstractmethod
    def unwrap(self) -> T:
        """
        Returns the contained Ok value.
        Raises an exception if the result is Err.
        """
        pass
    
    @abstractmethod
    def unwrap_or(self, default: T) -> T:
        """
        Returns the contained Ok value or a provided default.
        """
        pass
    
    @abstractmethod
    def unwrap_or_else(self, f: Callable[[E], T]) -> T:
        """
        Returns the contained Ok value or computes it from the error.
        """
        pass
    
    @abstractmethod
    def map(self, f: Callable[[T], U]) -> Result[U, E]:
        """
        Maps a Result<T, E> to Result<U, E> by applying a function to the Ok value.
        """
        pass
    
    @abstractmethod
    def map_err(self, f: Callable[[E], U]) -> Result[T, U]:
        """
        Maps a Result<T, E> to Result<T, U> by applying a function to the Err value.
        """
        pass
    
    @abstractmethod
    def and_then(self, f: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """
        Chains Result operations, also known as flatmap.
        """
        pass
    
    @abstractmethod
    def or_else(self, f: Callable[[E], Result[T, U]]) -> Result[T, U]:
        """
        Chains Result operations on the error case.
        """
        pass


class Ok(Result[T, E]):
    """Represents a successful result containing a value."""
    
    def __init__(self, value: T):
        self._value = value
    
    def is_ok(self) -> bool:
        return True
    
    def is_err(self) -> bool:
        return False
    
    def unwrap(self) -> T:
        return self._value
    
    def unwrap_or(self, default: T) -> T:
        return self._value
    
    def unwrap_or_else(self, f: Callable[[E], T]) -> T:
        return self._value
    
    def map(self, f: Callable[[T], U]) -> Result[U, E]:
        try:
            return Ok(f(self._value))
        except Exception as e:
            return Err(e)  # type: ignore
    
    def map_err(self, f: Callable[[E], U]) -> Result[T, U]:
        return Ok(self._value)
    
    def and_then(self, f: Callable[[T], Result[U, E]]) -> Result[U, E]:
        try:
            return f(self._value)
        except Exception as e:
            return Err(e)  # type: ignore
    
    def or_else(self, f: Callable[[E], Result[T, U]]) -> Result[T, U]:
        return Ok(self._value)
    
    def __repr__(self) -> str:
        return f"Ok({self._value!r})"
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Ok) and self._value == other._value


class Err(Result[T, E]):
    """Represents a failed result containing an error."""
    
    def __init__(self, error: E, *, _skip_logging: bool = False):
        self._error = error
        if not _skip_logging:
            self._log_error()
    
    def _log_error(self) -> None:
        """Log the error using configured logging settings."""
        config = get_config()
        
        # Check if logging is enabled globally
        if not config.enabled:
            return
            
        # Get the calling frame to capture context
        frame = inspect.currentframe()
        caller_frame = None
        library_name = "unknown"
        
        if frame and frame.f_back and frame.f_back.f_back:
            caller_frame = frame.f_back.f_back
            # Try to determine library name from the calling module
            if caller_frame.f_code.co_filename:
                # Extract library name from file path
                import os
                filename = caller_frame.f_code.co_filename
                # Simple heuristic: use the parent directory name
                library_name = os.path.basename(os.path.dirname(filename))
        
        # Check if logging is enabled for this library
        if not should_log_for_library(library_name):
            return
            
        # Capture context based on configuration
        context: dict[str, Any] = {}
        if config.capture_function_name and caller_frame:
            context["function"] = caller_frame.f_code.co_name
        if config.capture_filename and caller_frame:
            context["file"] = caller_frame.f_code.co_filename
        if config.capture_lineno and caller_frame:
            context["line"] = caller_frame.f_lineno
        if config.capture_locals and caller_frame:
            context["locals"] = {k: v for k, v in caller_frame.f_locals.items() 
                               if not k.startswith('_')}
        
        # Get log level for this library
        log_level = get_log_level_for_library(library_name).upper()
        
        # Build log message
        if config.format:
            message = config.format.format(error=self._error, **context)
        else:
            location = f"{context.get('function', '<?>')}:{context.get('line', '?')}"
            message = f"Result error in {location} - {self._error}"
        
        # Log at the configured level
        logger.log(log_level, message, **context, error=self._error)
    
    @classmethod
    def from_exception(cls, exception: Exception) -> Err[Any, Exception]:
        """Create an Err from an exception with automatic logging."""
        return Err[Any, Exception](exception)
    
    @classmethod
    def from_value(cls, error: E) -> Err[T, E]:
        """Create an Err from any error value with automatic logging."""
        return cls(error)
    
    def is_ok(self) -> bool:
        return False
    
    def is_err(self) -> bool:
        return True
    
    def unwrap(self) -> T:
        if isinstance(self._error, Exception):
            raise self._error
        else:
            raise RuntimeError(f"Called unwrap on Err: {self._error}")
    
    def unwrap_or(self, default: T) -> T:
        return default
    
    def unwrap_or_else(self, f: Callable[[E], T]) -> T:
        try:
            return f(self._error)
        except Exception as e:
            # If the unwrap_or_else function fails, we need to raise an error
            raise RuntimeError(f"unwrap_or_else function failed: {e}")
    
    def map(self, f: Callable[[T], U]) -> Result[U, E]:
        return Err(self._error, _skip_logging=True)
    
    def map_err(self, f: Callable[[E], U]) -> Result[T, U]:
        try:
            return Err(f(self._error))
        except Exception as e:
            return Err(e)  # type: ignore
    
    def and_then(self, f: Callable[[T], Result[U, E]]) -> Result[U, E]:
        return Err(self._error, _skip_logging=True)
    
    def or_else(self, f: Callable[[E], Result[T, U]]) -> Result[T, U]:
        try:
            return f(self._error)
        except Exception as e:
            return Err(e)  # type: ignore
    
    def __repr__(self) -> str:
        return f"Err({self._error!r})"
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Err) and self._error == other._error


# Convenience functions for creating Results
def from_callable(f: Callable[[], T]) -> Result[T, Exception]:
    """
    Execute a callable and return Ok(result) or Err(exception).
    """
    try:
        return Ok(f())
    except Exception as e:
        return Err.from_exception(e)


def from_optional(value: Optional[T], error: E) -> Result[T, E]:
    """
    Convert an Optional value to a Result.
    """
    if value is not None:
        return Ok(value)
    else:
        return Err.from_value(error)


