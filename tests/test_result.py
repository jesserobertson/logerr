"""
Tests for Result type with automatic logging.
"""

import pytest
from unittest.mock import patch
from loguru import logger

import logerr
from logerr import Result, Ok, Err, configure


class TestOk:
    """Tests for Ok class."""
    
    def test_ok_creation(self):
        result = Ok(42)
        assert result.is_ok()
        assert not result.is_err()
        assert result.unwrap() == 42
    
    def test_ok_unwrap_or(self):
        result = Ok(42)
        assert result.unwrap_or(0) == 42
    
    def test_ok_map(self):
        result = Ok(42)
        mapped = result.map(lambda x: x * 2)
        assert isinstance(mapped, Ok)
        assert mapped.unwrap() == 84
    
    def test_ok_and_then(self):
        result = Ok(42)
        chained = result.and_then(lambda x: Ok(x * 2))
        assert isinstance(chained, Ok)
        assert chained.unwrap() == 84
    
    def test_ok_map_with_exception(self):
        result = Ok(42)
        mapped = result.map(lambda x: 1 / 0)  # Will raise ZeroDivisionError
        assert isinstance(mapped, Err)


class TestErr:
    """Tests for Err class."""
    
    def test_err_creation(self):
        result = Err("error message")
        assert not result.is_ok()
        assert result.is_err()
    
    def test_err_unwrap_raises(self):
        result = Err(ValueError("test error"))
        with pytest.raises(ValueError, match="test error"):
            result.unwrap()
    
    def test_err_unwrap_or(self):
        result = Err("error")
        assert result.unwrap_or(42) == 42
    
    def test_err_map_returns_err(self):
        result = Err("error")
        mapped = result.map(lambda x: x * 2)
        assert isinstance(mapped, Err)
    
    def test_err_from_exception(self):
        exception = ValueError("test error")
        result = Err.from_exception(exception)
        assert isinstance(result, Err)
        assert result._error == exception


class TestResultFactories:
    """Tests for Result factory functions."""
    
    def test_result_from_callable_success(self):
        result = logerr.result.from_callable(lambda: 42)
        assert isinstance(result, Ok)
        assert result.unwrap() == 42
    
    def test_result_from_callable_exception(self):
        result = logerr.result.from_callable(lambda: 1 / 0)
        assert isinstance(result, Err)
        assert isinstance(result._error, ZeroDivisionError)


class TestLogging:
    """Tests for automatic logging functionality."""
    
    def setup_method(self):
        """Reset configuration before each test."""
        from logerr import reset_config
        reset_config()
    
    def test_err_logs_by_default(self):
        with patch.object(logger, 'log') as mock_log:
            Err("test error")
            mock_log.assert_called_once()
            
        # Check that the log call used ERROR level
        args, kwargs = mock_log.call_args
        assert args[0] == "ERROR"  # log level
        assert "test error" in args[1]  # message
    
    def test_err_logging_can_be_disabled(self):
        configure({"enabled": False})
        
        with patch.object(logger, 'log') as mock_log:
            Err("test error")
            mock_log.assert_not_called()
        
        # Reset config
        configure({"enabled": True})
    
    def test_custom_log_level(self):
        configure({"level": "WARNING"})
        
        with patch.object(logger, 'log') as mock_log:
            Err("test error")
            mock_log.assert_called_once()
            
        # Check that the log call used WARNING level
        args, kwargs = mock_log.call_args
        assert args[0] == "WARNING"
        
        # Reset config
        configure({"level": "ERROR"})
    
    def test_library_specific_config(self):
        configure({
            "libraries": {
                "tests": {"level": "INFO", "enabled": True}
            }
        })
        
        with patch.object(logger, 'log') as mock_log:
            Err("test error")
            mock_log.assert_called_once()
            
        args, kwargs = mock_log.call_args
        assert args[0] == "INFO"
        
        # Reset config
        configure({"libraries": {}})


class TestChaining:
    """Tests for Result chaining operations."""
    
    def test_ok_chain(self):
        result = (Ok(42)
                 .map(lambda x: x * 2)
                 .and_then(lambda x: Ok(x + 1))
                 .map(lambda x: str(x)))
        
        assert isinstance(result, Ok)
        assert result.unwrap() == "85"
    
    def test_err_chain_short_circuits(self):
        result = (Err("initial error")
                 .map(lambda x: x * 2)  # Should not execute
                 .and_then(lambda x: Ok(x + 1))  # Should not execute
                 .map(lambda x: str(x)))  # Should not execute
        
        assert isinstance(result, Err)
        assert result._error == "initial error"
    
    def test_mixed_chain_with_error(self):
        with patch.object(logger, 'log'):  # Suppress logging for test
            result = (Ok(42)
                     .map(lambda x: x * 2)  # 84
                     .map(lambda x: 1 / 0)  # Error here
                     .map(lambda x: str(x)))  # Should not execute
            
            assert isinstance(result, Err)
            assert isinstance(result._error, ZeroDivisionError)