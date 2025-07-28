"""
Tests for Option type with automatic logging.
"""

import pytest
from unittest.mock import patch
from loguru import logger

from logerr import Option, Some, Nothing, option_from_nullable, option_from_callable, option_from_predicate, configure


class TestSome:
    """Tests for Some class."""
    
    def test_some_creation(self):
        option = Some(42)
        assert option.is_some()
        assert not option.is_nothing()
        assert option.unwrap() == 42
    
    def test_some_unwrap_or(self):
        option = Some(42)
        assert option.unwrap_or(0) == 42
    
    def test_some_unwrap_or_else(self):
        option = Some(42)
        assert option.unwrap_or_else(lambda: 0) == 42
    
    def test_some_map(self):
        option = Some(42)
        mapped = option.map(lambda x: x * 2)
        assert isinstance(mapped, Some)
        assert mapped.unwrap() == 84
    
    def test_some_and_then(self):
        option = Some(42)
        chained = option.and_then(lambda x: Some(x * 2))
        assert isinstance(chained, Some)
        assert chained.unwrap() == 84
    
    def test_some_or_else(self):
        option = Some(42)
        result = option.or_else(lambda: Some(0))
        assert isinstance(result, Some)
        assert result.unwrap() == 42
    
    def test_some_filter_passes(self):
        option = Some(42)
        filtered = option.filter(lambda x: x > 30)
        assert isinstance(filtered, Some)
        assert filtered.unwrap() == 42
    
    def test_some_filter_fails(self):
        option = Some(42)
        filtered = option.filter(lambda x: x > 50)
        assert isinstance(filtered, Nothing)
    
    def test_some_map_with_exception(self):
        option = Some(42)
        mapped = option.map(lambda x: 1 / 0)  # Will raise ZeroDivisionError
        assert isinstance(mapped, Nothing)
    
    def test_some_map_returns_none(self):
        option = Some(42)
        mapped = option.map(lambda x: None)  # Returns None
        assert isinstance(mapped, Nothing)


class TestNothing:
    """Tests for Nothing class."""
    
    def test_nothing_creation(self):
        option = Nothing("test reason")
        assert not option.is_some()
        assert option.is_nothing()
    
    def test_nothing_unwrap_raises(self):
        option = Nothing("test reason")
        with pytest.raises(ValueError, match="Called unwrap on Nothing: test reason"):
            option.unwrap()
    
    def test_nothing_unwrap_or(self):
        option = Nothing("test reason")
        assert option.unwrap_or(42) == 42
    
    def test_nothing_unwrap_or_else(self):
        option = Nothing("test reason")
        assert option.unwrap_or_else(lambda: 42) == 42
    
    def test_nothing_map_returns_nothing(self):
        option = Nothing("test reason")
        mapped = option.map(lambda x: x * 2)
        assert isinstance(mapped, Nothing)
    
    def test_nothing_and_then_returns_nothing(self):
        option = Nothing("test reason")
        chained = option.and_then(lambda x: Some(x * 2))
        assert isinstance(chained, Nothing)
    
    def test_nothing_or_else(self):
        option = Nothing("test reason")
        result = option.or_else(lambda: Some(42))
        assert isinstance(result, Some)
        assert result.unwrap() == 42
    
    def test_nothing_filter_returns_nothing(self):
        option = Nothing("test reason")
        filtered = option.filter(lambda x: True)
        assert isinstance(filtered, Nothing)
    
    def test_nothing_from_exception(self):
        exception = ValueError("test error")
        option = Nothing.from_exception(exception)
        assert isinstance(option, Nothing)
        assert "Exception: test error" in option._reason
    
    def test_nothing_from_none(self):
        option = Nothing.from_none("custom reason")
        assert isinstance(option, Nothing)
        assert option._reason == "custom reason"
    
    def test_nothing_empty_no_logging(self):
        with patch.object(logger, 'log') as mock_log:
            option = Nothing.empty()
            mock_log.assert_not_called()


class TestOptionFactories:
    """Tests for Option factory functions."""
    
    def test_option_from_nullable_some(self):
        option = option_from_nullable(42)
        assert isinstance(option, Some)
        assert option.unwrap() == 42
    
    def test_option_from_nullable_nothing(self):
        option = option_from_nullable(None)
        assert isinstance(option, Nothing)
    
    def test_option_from_callable_some(self):
        option = option_from_callable(lambda: 42)
        assert isinstance(option, Some)
        assert option.unwrap() == 42
    
    def test_option_from_callable_none(self):
        option = option_from_callable(lambda: None)
        assert isinstance(option, Nothing)
    
    def test_option_from_callable_exception(self):
        option = option_from_callable(lambda: 1 / 0)
        assert isinstance(option, Nothing)
    
    def test_option_from_predicate_success(self):
        option = option_from_predicate(42, lambda x: x > 30)
        assert isinstance(option, Some)
        assert option.unwrap() == 42
    
    def test_option_from_predicate_failure(self):
        option = option_from_predicate(42, lambda x: x > 50)
        assert isinstance(option, Nothing)
    
    def test_option_from_predicate_exception(self):
        option = option_from_predicate(42, lambda x: 1 / 0)
        assert isinstance(option, Nothing)


class TestLogging:
    """Tests for automatic logging functionality."""
    
    def setup_method(self):
        """Reset configuration before each test."""
        from logerr import reset_config
        reset_config()
    
    def test_nothing_logs_by_default(self):
        with patch.object(logger, 'log') as mock_log:
            Nothing("test reason")
            mock_log.assert_called_once()
            
        # Check that the log call used WARNING level (default for Nothing)
        args, kwargs = mock_log.call_args
        assert args[0] == "WARNING"  # log level
        assert "test reason" in args[1]  # message
    
    def test_nothing_logging_can_be_disabled(self):
        configure({"enabled": False})
        
        with patch.object(logger, 'log') as mock_log:
            Nothing("test reason")
            mock_log.assert_not_called()
        
        # Reset config
        configure({"enabled": True})
    
    def test_custom_log_level(self):
        configure({"level": "INFO"})
        
        with patch.object(logger, 'log') as mock_log:
            Nothing("test reason")
            mock_log.assert_called_once()
            
        # Check that the log call used INFO level
        args, kwargs = mock_log.call_args
        assert args[0] == "INFO"
        
        # Reset config
        configure({"level": "ERROR"})
    
    def test_library_specific_config(self):
        configure({
            "libraries": {
                "tests": {"level": "DEBUG", "enabled": True}
            }
        })
        
        with patch.object(logger, 'log') as mock_log:
            Nothing("test reason")
            mock_log.assert_called_once()
            
        args, kwargs = mock_log.call_args
        assert args[0] == "DEBUG"
        
        # Reset config
        configure({"libraries": {}})


class TestChaining:
    """Tests for Option chaining operations."""
    
    def test_some_chain(self):
        option = (Some(42)
                 .map(lambda x: x * 2)
                 .and_then(lambda x: Some(x + 1))
                 .filter(lambda x: x > 80)
                 .map(lambda x: str(x)))
        
        assert isinstance(option, Some)
        assert option.unwrap() == "85"
    
    def test_nothing_chain_short_circuits(self):
        option = (Nothing.empty()  # Use empty() to avoid logging in test
                 .map(lambda x: x * 2)  # Should not execute
                 .and_then(lambda x: Some(x + 1))  # Should not execute
                 .filter(lambda x: x > 80)  # Should not execute
                 .map(lambda x: str(x)))  # Should not execute
        
        assert isinstance(option, Nothing)
    
    def test_mixed_chain_with_filter_failure(self):
        with patch.object(logger, 'log'):  # Suppress logging for test
            option = (Some(42)
                     .map(lambda x: x * 2)  # 84
                     .filter(lambda x: x > 100)  # Fails here
                     .map(lambda x: str(x)))  # Should not execute
            
            assert isinstance(option, Nothing)
    
    def test_chain_with_or_else_recovery(self):
        option = (Nothing.empty()
                 .map(lambda x: x * 2)
                 .or_else(lambda: Some(99))  # Recovery
                 .map(lambda x: str(x)))
        
        assert isinstance(option, Some)
        assert option.unwrap() == "99"


class TestIntegrationWithResult:
    """Tests for integration between Option and Result types."""
    
    def test_option_to_result_pattern(self):
        # Common pattern: convert Option to Result
        def option_to_result(opt):
            if opt.is_some():
                from logerr import Ok
                return Ok(opt.unwrap())
            else:
                from logerr import Err
                return Err(f"Option was Nothing: {opt._reason}")
        
        some_option = Some(42)
        nothing_option = Nothing.empty()
        
        result1 = option_to_result(some_option)
        result2 = option_to_result(nothing_option)
        
        assert result1.is_ok()
        assert result1.unwrap() == 42
        
        assert result2.is_err()
        assert "Option was Nothing" in str(result2._error)