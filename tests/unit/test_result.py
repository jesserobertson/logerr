"""
Tests for Result type with automatic logging.
"""

from unittest.mock import patch

import pytest
from loguru import logger

import logerr
from logerr import Err, Ok, configure

pytestmark = pytest.mark.unit


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

    def test_ok_then(self):
        result = Ok(42)
        chained = result.then(lambda x: Ok(x * 2))
        assert isinstance(chained, Ok)
        assert chained.unwrap() == 84

    def test_ok_then_exception_handling(self):
        """Test that Ok.then handles exceptions in callback functions."""

        def failing_func(x):
            raise ValueError("test error")

        result = Ok(42).then(failing_func)
        assert result.is_err()
        assert isinstance(result, Err)

    def test_ok_map_with_exception(self):
        result = Ok(42)
        mapped = result.map(lambda x: 1 / 0)  # Will raise ZeroDivisionError
        assert isinstance(mapped, Err)

    def test_ok_unwrap_err_raises(self):
        result = Ok(42)
        with pytest.raises(RuntimeError, match="Called unwrap_err on Ok: 42"):
            result.unwrap_err()

    def test_ok_or_else_returns_self_value(self):
        result = Ok(42)
        recovered = result.or_else(lambda e: Ok(0))
        assert isinstance(recovered, Ok)
        assert recovered.unwrap() == 42

    def test_ok_map_err_returns_ok_unchanged(self):
        result = Ok(42)
        mapped = result.map_err(str)
        assert isinstance(mapped, Ok)
        assert mapped.unwrap() == 42

    def test_ok_repr(self):
        assert repr(Ok(42)) == "Ok(42)"


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

    def test_err_unwrap_non_exception_error_raises_runtime_error(self):
        """Err.unwrap() falls back to RuntimeError when the error isn't an Exception."""
        result = Err("plain string error")
        with pytest.raises(
            RuntimeError, match="Called unwrap on Err: plain string error"
        ):
            result.unwrap()

    def test_err_unwrap_or_else_exception_handling(self):
        """Test that Err.unwrap_or_else raises RuntimeError if the callback fails."""
        result = Err("original error")

        def failing_func(e):
            raise ValueError("callback failed")

        with pytest.raises(RuntimeError, match="unwrap_or_else function failed"):
            result.unwrap_or_else(failing_func)

    def test_err_map_err_exception_handling(self):
        """Test that Err.map_err handles exceptions raised by the transform."""
        result = Err("original error")

        def failing_transform(e):
            raise ValueError("transform failed")

        mapped = result.map_err(failing_transform)
        assert isinstance(mapped, Err)
        assert isinstance(mapped._error, ValueError)

    def test_err_or_else_recovers(self):
        """Test that Err.or_else invokes the recovery function."""
        result = Err("original error")
        recovered = result.or_else(lambda e: Ok(99))
        assert isinstance(recovered, Ok)
        assert recovered.unwrap() == 99

    def test_err_or_else_exception_handling(self):
        """Test that Err.or_else handles exceptions raised by the recovery function."""
        result = Err("original error")

        def failing_recovery(e):
            raise RuntimeError("recovery failed")

        recovered = result.or_else(failing_recovery)
        assert isinstance(recovered, Err)
        assert isinstance(recovered._error, RuntimeError)

    def test_err_repr(self):
        assert repr(Err("boom")) == "Err('boom')"

    def test_err_lt_type_error_returns_not_implemented(self):
        """Err.__lt__ should defer to NotImplemented when values aren't orderable."""

        class NonComparable:
            pass

        err1 = Err(NonComparable())
        err2 = Err(NonComparable())
        with pytest.raises(TypeError):
            assert err1 < err2

    def test_err_lt_incomparable_type_returns_not_implemented(self):
        err = Err("error")
        with pytest.raises(TypeError):
            assert err < 5

    def test_err_gt_type_error_returns_not_implemented(self):
        """Err.__gt__ should defer to NotImplemented when values aren't orderable."""

        class NonComparable:
            pass

        err1 = Err(NonComparable())
        err2 = Err(NonComparable())
        with pytest.raises(TypeError):
            assert err1 > err2

    def test_err_gt_incomparable_type_returns_not_implemented(self):
        err = Err("error")
        with pytest.raises(TypeError):
            assert err > 5


class TestResultFactories:
    """Tests for Result factory functions."""

    def test_result_of_success(self):
        result = logerr.result.of(lambda: 42)
        assert isinstance(result, Ok)
        assert result.unwrap() == 42

    def test_result_of_exception(self):
        result = logerr.result.of(lambda: 1 / 0)
        assert isinstance(result, Err)
        assert isinstance(result._error, ZeroDivisionError)

    def test_result_from_optional_classmethod(self):
        """Test the Result.from_optional() ABC classmethod delegates correctly."""
        from logerr import Result

        result = Result.from_optional("value", "was none")
        assert isinstance(result, Ok)
        assert result.unwrap() == "value"

        result_none = Result.from_optional(None, "was none")
        assert isinstance(result_none, Err)
        assert result_none.unwrap_err() == "was none"

    def test_result_from_predicate_classmethod(self):
        """Test the Result.from_predicate() ABC classmethod delegates correctly."""
        from logerr import Result

        result = Result.from_predicate(42, lambda x: x > 30, "too small")
        assert isinstance(result, Ok)
        assert result.unwrap() == 42


class TestLogging:
    """Tests for automatic logging functionality."""

    def setup_method(self):
        """Reset configuration before each test."""
        from logerr import reset_config

        reset_config()

    def test_err_logs_by_default(self):
        with patch.object(logger, "bind") as mock_bind:
            mock_bound = mock_bind.return_value
            Err("test error")
            mock_bind.assert_called_once()
            mock_bound.log.assert_called_once()

        # Check that the log call used ERROR level
        args, kwargs = mock_bound.log.call_args
        assert args[0] == "ERROR"  # log level
        assert "test error" in args[1]  # message

    def test_err_logging_can_be_disabled(self):
        configure(enabled=False)

        with patch.object(logger, "bind") as mock_bind:
            Err("test error")
            mock_bind.assert_not_called()

        # Reset config
        configure(enabled=True)

    def test_custom_log_level(self):
        configure(level="WARNING")

        with patch.object(logger, "bind") as mock_bind:
            mock_bound = mock_bind.return_value
            Err("test error")
            mock_bind.assert_called_once()
            mock_bound.log.assert_called_once()

        # Check that the log call used WARNING level
        args, kwargs = mock_bound.log.call_args
        assert args[0] == "WARNING"

        # Reset config
        configure(level="ERROR")

    @pytest.mark.skip(reason="Library-specific config moved to recipes module")
    def test_library_specific_config(self):
        # This test is for advanced configuration features
        pass


class TestChaining:
    """Tests for Result chaining operations."""

    def test_ok_chain(self):
        result = (
            Ok(42).map(lambda x: x * 2).then(lambda x: Ok(x + 1)).map(lambda x: str(x))
        )

        assert isinstance(result, Ok)
        assert result.unwrap() == "85"

    def test_err_chain_short_circuits(self):
        result = (
            Err("initial error")
            .map(lambda x: x * 2)  # Should not execute
            .then(lambda x: Ok(x + 1))  # Should not execute
            .map(lambda x: str(x))
        )  # Should not execute

        assert isinstance(result, Err)
        assert result._error == "initial error"

    def test_mixed_chain_with_error(self):
        with patch.object(logger, "log"):  # Suppress logging for test
            result = (
                Ok(42)
                .map(lambda x: x * 2)  # 84
                .map(lambda x: 1 / 0)  # Error here
                .map(lambda x: str(x))
            )  # Should not execute

            assert isinstance(result, Err)
            assert isinstance(result._error, ZeroDivisionError)
