"""
Option type implementation with automatic logging integration.

Provides Rust-like Option<T> types with automatic logging of None cases
through loguru, configurable via confection.
"""

from __future__ import annotations

import inspect
from typing import TypeVar, Generic, Union, Callable, Any, Optional
from abc import ABC, abstractmethod

from loguru import logger

from .config import get_config, should_log_for_library, get_log_level_for_library

T = TypeVar('T')
U = TypeVar('U')


class Option(Generic[T], ABC):
    """
    A type that represents an optional value: either Some(T) or Nothing.
    
    Similar to Rust's Option<T> type, with automatic logging integration
    for Nothing cases when they represent errors or unexpected conditions.
    """
    
    @abstractmethod
    def is_some(self) -> bool:
        """Returns True if the option is Some."""
        pass
    
    @abstractmethod
    def is_nothing(self) -> bool:
        """Returns True if the option is Nothing."""
        pass
    
    @abstractmethod
    def unwrap(self) -> T:
        """
        Returns the contained Some value.
        Raises an exception if the option is Nothing.
        """
        pass
    
    @abstractmethod
    def unwrap_or(self, default: T) -> T:
        """
        Returns the contained Some value or a provided default.
        """
        pass
    
    @abstractmethod
    def unwrap_or_else(self, f: Callable[[], T]) -> T:
        """
        Returns the contained Some value or computes it from a closure.
        """
        pass
    
    @abstractmethod
    def map(self, f: Callable[[T], U]) -> Option[U]:
        """
        Maps an Option<T> to Option<U> by applying a function to the Some value.
        """
        pass
    
    @abstractmethod
    def and_then(self, f: Callable[[T], Option[U]]) -> Option[U]:
        """
        Chains Option operations, also known as flatmap.
        """
        pass
    
    @abstractmethod
    def or_else(self, f: Callable[[], Option[T]]) -> Option[T]:
        """
        Chains Option operations on the Nothing case.
        """
        pass
    
    @abstractmethod
    def filter(self, predicate: Callable[[T], bool]) -> Option[T]:
        """
        Returns Nothing if the option is Nothing, otherwise calls predicate
        with the wrapped value and returns Some(t) if predicate returns True,
        otherwise returns Nothing.
        """
        pass


class Some(Option[T]):
    """Represents an option containing a value."""
    
    def __init__(self, value: T):
        self._value = value
    
    def is_some(self) -> bool:
        return True
    
    def is_nothing(self) -> bool:
        return False
    
    def unwrap(self) -> T:
        return self._value
    
    def unwrap_or(self, default: T) -> T:
        return self._value
    
    def unwrap_or_else(self, f: Callable[[], T]) -> T:
        return self._value
    
    def map(self, f: Callable[[T], U]) -> Option[U]:
        try:
            result = f(self._value)
            if result is None:
                return Nothing.from_none("Map function returned None")
            return Some(result)
        except Exception as e:
            return Nothing.from_exception(e)
    
    def and_then(self, f: Callable[[T], Option[U]]) -> Option[U]:
        try:
            return f(self._value)
        except Exception as e:
            return Nothing.from_exception(e)
    
    def or_else(self, f: Callable[[], Option[T]]) -> Option[T]:
        return self
    
    def filter(self, predicate: Callable[[T], bool]) -> Option[T]:
        try:
            if predicate(self._value):
                return self
            else:
                return Nothing.from_filter("Value did not pass filter predicate")
        except Exception as e:
            return Nothing.from_exception(e)
    
    def __repr__(self) -> str:
        return f"Some({self._value!r})"
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Some) and self._value == other._value


class Nothing(Option[T]):
    """Represents an option with no value."""
    
    def __init__(self, reason: str = "No value", *, _skip_logging: bool = False):
        self._reason = reason
        if not _skip_logging:
            self._log_nothing()
    
    def _log_nothing(self) -> None:
        """Log the Nothing case using configured logging settings."""
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
        
        # Get log level for this library (default to WARNING for Nothing cases)
        log_level = get_log_level_for_library(library_name).upper()
        # For Nothing cases, we might want to use a lower severity by default
        if log_level == "ERROR":
            log_level = "WARNING"
        
        # Build log message
        if config.format:
            message = config.format.format(reason=self._reason, **context)
        else:
            location = f"{context.get('function', '<?>')}:{context.get('line', '?')}"
            message = f"Option Nothing in {location} - {self._reason}"
        
        # Log at the configured level
        logger.log(log_level, message, **context, reason=self._reason)
    
    @classmethod
    def from_exception(cls, exception: Exception) -> Nothing[T]:
        """Create a Nothing from an exception with automatic logging."""
        return cls(f"Exception: {exception}")
    
    @classmethod
    def from_none(cls, reason: str = "Value was None") -> Nothing[T]:
        """Create a Nothing from a None value with automatic logging."""
        return cls(reason)
    
    @classmethod
    def from_filter(cls, reason: str = "Filter condition failed") -> Nothing[T]:
        """Create a Nothing from a failed filter with automatic logging."""
        return cls(reason)
    
    @classmethod
    def empty(cls) -> Nothing[T]:
        """Create a Nothing without logging (for normal control flow)."""
        return cls("Empty option", _skip_logging=True)
    
    def is_some(self) -> bool:
        return False
    
    def is_nothing(self) -> bool:
        return True
    
    def unwrap(self) -> T:
        raise ValueError(f"Called unwrap on Nothing: {self._reason}")
    
    def unwrap_or(self, default: T) -> T:
        return default
    
    def unwrap_or_else(self, f: Callable[[], T]) -> T:
        try:
            return f()
        except Exception as e:
            # If the unwrap_or_else function fails, we need to raise an error
            raise ValueError(f"unwrap_or_else function failed: {e}")
    
    def map(self, f: Callable[[T], U]) -> Option[U]:
        return Nothing(self._reason, _skip_logging=True)
    
    def and_then(self, f: Callable[[T], Option[U]]) -> Option[U]:
        return Nothing(self._reason, _skip_logging=True)
    
    def or_else(self, f: Callable[[], Option[T]]) -> Option[T]:
        try:
            return f()
        except Exception as e:
            return Nothing.from_exception(e)
    
    def filter(self, predicate: Callable[[T], bool]) -> Option[T]:
        return Nothing(self._reason, _skip_logging=True)
    
    def __repr__(self) -> str:
        return f"Nothing({self._reason!r})"
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Nothing) and self._reason == other._reason


# Convenience functions for creating Options
def from_nullable(value: Optional[T]) -> Option[T]:
    """
    Convert a nullable value to an Option.
    """
    if value is not None:
        return Some(value)
    else:
        return Nothing.from_none()


def from_callable(f: Callable[[], Optional[T]]) -> Option[T]:
    """
    Execute a callable and return Some(result) or Nothing.
    """
    try:
        result = f()
        if result is not None:
            return Some(result)
        else:
            return Nothing.from_none("Callable returned None")
    except Exception as e:
        return Nothing.from_exception(e)


def from_predicate(value: T, predicate: Callable[[T], bool]) -> Option[T]:
    """
    Create an Option based on whether a value satisfies a predicate.
    """
    try:
        if predicate(value):
            return Some(value)
        else:
            return Nothing.from_filter(f"Value {value} failed predicate")
    except Exception as e:
        return Nothing.from_exception(e)


