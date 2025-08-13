"""
Tests for Option type with automatic logging.
"""

from unittest.mock import patch

import pytest
from loguru import logger

import logerr
from logerr import Nothing, Some, configure


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

    def test_some_then(self):
        option = Some(42)
        chained = option.then(lambda x: Some(x * 2))
        assert isinstance(chained, Some)
        assert chained.unwrap() == 84

    def test_some_or_else(self):
        option = Some(42)
        result = option.unwrap_or(0)
        assert result == 42

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

    def test_some_then_exception_handling(self):
        """Test that Some.then handles exceptions in callback functions."""

        def failing_func(x):
            raise ValueError("test error")

        result = Some(42).then(failing_func)
        assert result.is_nothing()
        assert isinstance(result, Nothing)


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

    def test_nothing_unwrap_or_else_exception(self):
        """Test that Nothing.unwrap_or_else handles exceptions in callback functions."""

        def failing_func():
            raise RuntimeError("callback failed")

        nothing = Nothing("test reason")
        with pytest.raises(ValueError, match="unwrap_or_else function failed"):
            nothing.unwrap_or_else(failing_func)

    def test_nothing_map_returns_nothing(self):
        option = Nothing("test reason")
        mapped = option.map(lambda x: x * 2)
        assert isinstance(mapped, Nothing)

    def test_nothing_then_returns_nothing(self):
        option = Nothing("test reason")
        chained = option.then(lambda x: Some(x * 2))
        assert isinstance(chained, Nothing)

    def test_nothing_or_else(self):
        option = Nothing("test reason")
        result = option.unwrap_or(42)
        assert result == 42

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
        with patch.object(logger, "log") as mock_log:
            Nothing.empty()
            mock_log.assert_not_called()


class TestOptionFactories:
    """Tests for Option factory functions."""

    def test_option_from_nullable_some(self):
        option = logerr.option.from_nullable(42)
        assert isinstance(option, Some)
        assert option.unwrap() == 42

    def test_option_from_nullable_nothing(self):
        option = logerr.option.from_nullable(None)
        assert isinstance(option, Nothing)

    def test_option_of_some(self):
        option = logerr.option.of(lambda: 42)
        assert isinstance(option, Some)
        assert option.unwrap() == 42

    def test_option_of_none(self):
        option = logerr.option.of(lambda: None)
        assert isinstance(option, Nothing)

    def test_option_of_exception(self):
        option = logerr.option.of(lambda: 1 / 0)
        assert isinstance(option, Nothing)

    def test_option_from_predicate_success(self):
        option = logerr.option.from_predicate(42, lambda x: x > 30)
        assert isinstance(option, Some)
        assert option.unwrap() == 42

    def test_option_from_predicate_failure(self):
        option = logerr.option.from_predicate(42, lambda x: x > 50)
        assert isinstance(option, Nothing)

    def test_option_from_predicate_exception(self):
        option = logerr.option.from_predicate(42, lambda x: 1 / 0)
        assert isinstance(option, Nothing)


class TestLogging:
    """Tests for automatic logging functionality."""

    def setup_method(self):
        """Reset configuration before each test."""
        from logerr import reset_config

        reset_config()

    def test_nothing_logs_by_default(self):
        with patch.object(logger, "bind") as mock_bind:
            mock_bound = mock_bind.return_value
            Nothing("test reason")
            mock_bind.assert_called_once()
            mock_bound.log.assert_called_once()

        # Check that the log call used WARNING level (default for Nothing)
        args, kwargs = mock_bound.log.call_args
        assert args[0] == "WARNING"  # log level
        assert "test reason" in args[1]  # message

    def test_nothing_logging_can_be_disabled(self):
        configure(enabled=False)

        with patch.object(logger, "bind") as mock_bind:
            Nothing("test reason")
            mock_bind.assert_not_called()

        # Reset config
        configure(enabled=True)

    def test_custom_log_level(self):
        configure(level="INFO")

        with patch.object(logger, "bind") as mock_bind:
            mock_bound = mock_bind.return_value
            Nothing("test reason")
            mock_bind.assert_called_once()
            mock_bound.log.assert_called_once()

        # Check that the log call used INFO level
        args, kwargs = mock_bound.log.call_args
        assert args[0] == "INFO"

        # Reset config
        configure(level="ERROR")

    @pytest.mark.skip(reason="Library-specific config moved to recipes module")
    def test_library_specific_config(self):
        # This test is for advanced configuration features
        pass

    @pytest.mark.skip(reason="Per-library logging moved to recipes module")
    def test_should_log_when_disabled(self):
        """Test should_log_for_library when logging is disabled globally."""
        # This test is for advanced configuration features
        pass

    @pytest.mark.skip(reason="configure_from_confection moved to recipes module")
    def test_configure_from_confection_no_logerr_key(self):
        """Test configure_from_confection when config file doesn't contain 'logerr' key."""
        import os

        # Create a temporary config file without 'logerr' section
        import tempfile

        from logerr.config import configure_from_confection, get_config

        with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
            f.write('[other_section]\nsome_setting = "value"\n')
            temp_config_path = f.name

        try:
            # This should not raise an error, just do nothing
            configure_from_confection(temp_config_path)

            # Configuration should remain at default values
            config = get_config()
            assert config.enabled is True

        finally:
            os.unlink(temp_config_path)


class TestChaining:
    """Tests for Option chaining operations."""

    def test_some_chain(self):
        option = (
            Some(42)
            .map(lambda x: x * 2)
            .then(lambda x: Some(x + 1))
            .filter(lambda x: x > 80)
            .map(lambda x: str(x))
        )

        assert isinstance(option, Some)
        assert option.unwrap() == "85"

    def test_nothing_chain_short_circuits(self):
        option = (
            Nothing.empty()  # Use empty() to avoid logging in test
            .map(lambda x: x * 2)  # Should not execute
            .then(lambda x: Some(x + 1))  # Should not execute
            .filter(lambda x: x > 80)  # Should not execute
            .map(lambda x: str(x))
        )  # Should not execute

        assert isinstance(option, Nothing)

    def test_mixed_chain_with_filter_failure(self):
        with patch.object(logger, "log"):  # Suppress logging for test
            option = (
                Some(42)
                .map(lambda x: x * 2)  # 84
                .filter(lambda x: x > 100)  # Fails here
                .map(lambda x: str(x))
            )  # Should not execute

            assert isinstance(option, Nothing)

    def test_chain_with_or_else_recovery(self):
        option = (
            Nothing.empty()
            .map(lambda x: x * 2)
            .or_default(99)  # Recovery
            .map(lambda x: str(x))
        )

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
